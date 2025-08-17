"""
Bootstrap manager for Pico W.

Provides an immortal control loop that manages WiFi/MQTT connectivity,
application lifecycle, SOS signaling, and OTA update handling.

This module is part of the bootstrap layer and must never be updated by OTA.
"""
# Reason: Centralize resilient logic here; keep imports minimal and avoid heavy deps.

try:
    from .http_updater import HttpUpdater
except ImportError:
    try:
        from http_updater import HttpUpdater  # type: ignore
    except Exception:
        HttpUpdater = None  # type: ignore

# Optional shared helpers (available in repo, may be missing on first flash)
try:
    from shared.wifi_manager import connect as wifi_connect, is_connected as wifi_is_connected
except Exception:
    wifi_connect = None  # type: ignore
    wifi_is_connected = None  # type: ignore

try:
    from shared.mqtt_client import Mqtt
except Exception:
    Mqtt = None  # type: ignore

try:
    import ujson as json  # type: ignore
except Exception:
    import json  # type: ignore

import time


class BootstrapManager:
    """
    Coordinates the bootstrap responsibilities and runs forever.

    Attributes:
        device_id (str): Unique identifier for the device.
        updater (HttpUpdater | None): HTTP updater instance for OTA.
    """

    def __init__(self, device_id: str = "device-unknown", wifi_ssid: str = "", wifi_password: str = "", mqtt_host: str = "", mqtt_port: int = 1883):
        """
        Initialize the bootstrap manager with safe defaults.

        Args:
            device_id (str): Stable, hardcoded ID for the device.
        """
        self.device_id = device_id
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port

        self.updater = HttpUpdater() if HttpUpdater else None
        self.mqtt = None
        self._sos_warned_wifi = False
        self._last_health_ms = 0

    def run_forever(self) -> None:
        """
        Enter the immortal bootstrap loop. Never returns.

        Returns:
            None: The loop is designed to run indefinitely.
        """
        while True:
            try:
                self._ensure_network()
                self._ensure_mqtt()
                self._process_commands_nonblocking()
                self._maybe_publish_health()
                self._load_and_run_application()
            except Exception as exc:
                # Capture and report errors but never exit the loop
                self._publish_sos("bootstrap_exception", str(exc))
                self._enter_help_mode()
                # After help mode, loop continues for recovery attempts

    # --- Connectivity -----------------------------------------------------
    def _ensure_network(self) -> None:
        """
        Ensure WiFi is connected. Implement retry with backoff.

        Returns:
            None
        """
        if wifi_is_connected and wifi_is_connected():
            return
        if not self.wifi_ssid or not self.wifi_password or not wifi_connect:
            if not self._sos_warned_wifi:
                self._publish_sos("wifi_config_missing", "SSID/PASSWORD not set or WiFi helper unavailable")
                self._sos_warned_wifi = True
            # Avoid tight loop
            time.sleep_ms(500)
            return
        # basic retry
        ok = wifi_connect(self.wifi_ssid, self.wifi_password, timeout_ms=8000, retry_delay_ms=250)
        if not ok:
            self._publish_sos("wifi_connect_failed", "Unable to connect to WiFi")
            time.sleep_ms(500)

    def _ensure_mqtt(self) -> None:
        """
        Ensure MQTT is connected and subscribed to system topics.

        Returns:
            None
        """
        if not self.mqtt and Mqtt and self.mqtt_host:
            self.mqtt = Mqtt(self.mqtt_host, self.mqtt_port)
            # Register message handler
            self.mqtt.set_message_handler(self._on_mqtt_message)
            # Configure LWT: retained offline health
            base = "home/system/{}/".format(self.device_id)
            lwt_topic = base + "health"
            try:
                self.mqtt.set_last_will(lwt_topic, "offline", retain=True, qos=0)
            except Exception:
                pass

        if not self.mqtt:
            return

        connected = self.mqtt.connect()
        if not connected:
            time.sleep_ms(300)
            return
        # Subscribe to system topics for this device
        base = "home/system/{}/".format(self.device_id)
        self.mqtt.subscribe(base + "update")
        self.mqtt.subscribe(base + "ping")
        # On fresh connect, publish boot + health online and version
        self._publish_health("online", retain=True)
        self._publish_boot()
        self._publish_version("unknown")

    # --- Commands & OTA ---------------------------------------------------
    def _process_commands_nonblocking(self) -> None:
        """
        Pump incoming MQTT messages and handle update/ping commands.

        Returns:
            None
        """
        try:
            if self.mqtt:
                self.mqtt.check_msg()
        except Exception:
            # Allow loop to continue; connectivity will be re-established
            pass

    def _handle_update(self, payload: dict) -> None:
        """
        Execute an OTA update request using the HTTP updater.

        Args:
            payload (dict): Update descriptor (e.g., file list or manifest URL).
        """
        if not self.updater:
            self._publish_sos("updater_missing", "HttpUpdater unavailable")
            return
        try:
            self._publish_status("updating")
            self.updater.download_and_apply(payload)
            self._publish_status("updated")
        except Exception as exc:
            self._publish_sos("update_failed", str(exc))

    # --- Application Lifecycle -------------------------------------------
    def _load_and_run_application(self) -> None:
        """
        Import and execute the replaceable application layer.

        Returns:
            None
        """
        try:
            # Convention: application entrypoint lives at /app/main.py with main()
            try:
                from app.main import main as app_main  # type: ignore
            except ImportError:
                # Fallback when files are deployed to root
                from app_main import main as app_main  # type: ignore
            self._publish_status("running")
            app_main()
        except Exception as exc:
            # Never crash the bootstrap; report and continue
            self._publish_sos("app_crash", str(exc))
            # Let the loop continue, enabling update or manual fix

    # --- SOS & Status -----------------------------------------------------
    def _publish_sos(self, error_type: str, details: str) -> None:
        """
        Publish a SOS message with details for human-in-the-loop recovery.

        Args:
            error_type (str): Classification of the error.
            details (str): Human-readable error details.
        """
        # Publish to MQTT if available; otherwise print as fallback.
        payload = {
            "error": error_type,
            "details": details,
            "timestamp": self._now_ms(),
            "device_id": self.device_id,
        }
        topic = "home/system/{}/sos".format(self.device_id)
        sent = False
        try:
            if self.mqtt:
                sent = self.mqtt.publish(topic, json.dumps(payload))
        except Exception:
            sent = False
        if not sent:
            try:
                print("[SOS]", payload)
            except Exception:
                pass

    def _publish_status(self, status: str) -> None:
        """
        Publish a lightweight status update (e.g., running, updating).

        Args:
            status (str): Status string.
        """
        topic = "home/system/{}/status".format(self.device_id)
        sent = False
        try:
            if self.mqtt:
                sent = self.mqtt.publish(topic, status)
        except Exception:
            sent = False
        if not sent:
            try:
                print("[STATUS]", self.device_id, status)
            except Exception:
                pass

    def _publish_health(self, state: str, retain: bool = False) -> None:
        """
        Publish device health state (e.g., online/offline/needs_help).

        Args:
            state (str): Health state string.
            retain (bool): Retain flag for broker.
        """
        topic = "home/system/{}/health".format(self.device_id)
        try:
            if self.mqtt:
                self.mqtt.publish(topic, state, retain=retain)
            else:
                print("[HEALTH]", self.device_id, state)
        except Exception:
            try:
                print("[HEALTH]", self.device_id, state)
            except Exception:
                pass

    def _publish_boot(self) -> None:
        """
        Publish boot notification once after MQTT connect.
        """
        topic = "home/system/{}/boot".format(self.device_id)
        try:
            if self.mqtt:
                self.mqtt.publish(topic, str(self._now_ms()))
        except Exception:
            pass

    def _publish_version(self, version: str) -> None:
        """
        Publish current application version (commit sha or 'unknown').
        """
        topic = "home/system/{}/version".format(self.device_id)
        try:
            if self.mqtt:
                self.mqtt.publish(topic, version, retain=True)
        except Exception:
            pass

    def _maybe_publish_health(self) -> None:
        """
        Periodically publish health heartbeat.
        """
        try:
            now = self._now_ms()
            if now and (now - self._last_health_ms) >= 30000:  # 30s
                self._last_health_ms = now
                self._publish_health("online")
        except Exception:
            pass

    # --- Help Mode --------------------------------------------------------
    def _enter_help_mode(self) -> None:
        """
        Enter a responsive help mode awaiting human intervention.

        Returns:
            None
        """
        # Keep MQTT pumping lightly; avoid tight spin
        for _ in range(200):
            try:
                if self.mqtt:
                    self.mqtt.check_msg()
            except Exception:
                pass
            time.sleep_ms(100)

    # --- MQTT message handler --------------------------------------------
    def _on_mqtt_message(self, topic: str, msg: bytes) -> None:
        """
        Handle incoming MQTT messages for system topics.

        Args:
            topic (str): Full MQTT topic.
            msg (bytes): Message payload.
        """
        base = "home/system/{}/".format(self.device_id)
        if topic == base + "update":
            try:
                payload = json.loads(msg.decode())
            except Exception as exc:
                self._publish_sos("bad_update_payload", str(exc))
                return
            self._handle_update(payload)
        elif topic == base + "ping":
            self._publish_status("alive")

    # --- time helper ------------------------------------------------------
    def _now_ms(self) -> int:
        try:
            return time.ticks_ms()
        except Exception:
            return 0
