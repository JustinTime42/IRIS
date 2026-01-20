"""
Garage Controller Pico W Application

Controls and monitors:
- Garage door (relay + reed switches)
- Flood light (relay)

Entry point: init(runtime)
"""

try:
    import time
    import gc
except Exception:
    import sys as time  # type: ignore
    import sys as gc  # type: ignore
try:
    import machine
except Exception:
    import sys as machine  # type: ignore
from machine import Pin
from shared.config_manager import load_device_config
from shared.device_logger import DeviceLogger, set_global_logger
try:
    import ujson as json  # type: ignore
except Exception:
    import json  # type: ignore

# Pin Definitions
GARAGE_DOOR_RELAY = 2
FLOOD_LIGHT_RELAY = 5
DOOR_OPEN_SW = 3
DOOR_CLOSED_SW = 4
LED_PIN = 'LED'  # Built-in LED
# Active-low configuration for flood light relay: many modules energize on logic 0
LIGHT_RELAY_ACTIVE_LOW = True

# MQTT Topics
TOPIC_DOOR_STATUS = 'home/garage/door/status'
TOPIC_DOOR_COMMAND = 'home/garage/door/command'
TOPIC_LIGHT_STATUS = 'home/garage/light/status'
TOPIC_LIGHT_COMMAND = 'home/garage/light/command'
# Consolidated status topic
TOPIC_STATUS = 'home/garage-controller/status'


class GarageController:
    """Main controller for garage door and flood light.

    Attributes:
        runtime: Bootstrap-provided runtime with publish/subscribe/sos APIs.
        device_id (str): Device ID from config.
        led (machine.Pin): Built-in LED pin for heartbeat.
        door_relay (machine.Pin): Output to garage door relay.
        light_relay (machine.Pin): Output to flood light relay.
        door_open_sw (machine.Pin): Input from "door open" reed switch (active-low).
        door_closed_sw (machine.Pin): Input from "door closed" reed switch (active-low).
        last_door_state (str): Last published door state.
        last_light_state (bool): Last known flood light state.
        last_update (int): ms timestamp for periodic status update.
    """

    def __init__(self, runtime, device_id: str):
        """Initialize hardware and MQTT client.

        Args:
            runtime: Bootstrap-provided runtime with publish/subscribe/sos APIs.
            device_id: Device identifier from config.
        """
        self.runtime = runtime
        self.device_id = device_id
        self._sos_topic = "home/system/{}/sos".format(self.device_id)
        self._boot_time = time.ticks_ms()

        # Active errors list for consolidated status
        self._errors = []

        # Initialize enhanced logging
        try:
            self.logger = DeviceLogger(runtime, device_id, min_level='DEBUG')
            set_global_logger(self.logger)
            self.logger.info("app", "Garage controller initializing", {
                "version": "3.0.0",
                "features": ["door_control", "flood_light"],
                "pin_config": {
                    "door_relay": GARAGE_DOOR_RELAY,
                    "light_relay": FLOOD_LIGHT_RELAY,
                    "door_switches": [DOOR_OPEN_SW, DOOR_CLOSED_SW]
                }
            })
        except Exception as e:
            print("[ERROR] Failed to initialize logger: {}".format(e))
            self.logger = None

        try:
            self.led = Pin(LED_PIN, Pin.OUT)
            self.log_info("hardware", "LED initialized", {"pin": LED_PIN})

            # Initialize relays
            self.door_relay = Pin(GARAGE_DOOR_RELAY, Pin.OUT, value=0)  # Active high
            self.light_relay = Pin(FLOOD_LIGHT_RELAY, Pin.OUT, value=(0 if LIGHT_RELAY_ACTIVE_LOW else 1))  # Default ON at boot
            self.log_info("hardware", "Relays initialized", {
                "door_relay": GARAGE_DOOR_RELAY,
                "light_relay": FLOOD_LIGHT_RELAY,
                "light_active_low": LIGHT_RELAY_ACTIVE_LOW
            })
        except Exception as e:
            self.log_error("hardware", "Failed to initialize relays", {"error": str(e)})
            raise

        # Initialize door sensors with pull-ups
        try:
            self.door_open_sw = Pin(DOOR_OPEN_SW, Pin.IN, Pin.PULL_UP)
            self.door_closed_sw = Pin(DOOR_CLOSED_SW, Pin.IN, Pin.PULL_UP)
            self.log_info("hardware", "Door sensors initialized", {
                "open_switch": DOOR_OPEN_SW,
                "closed_switch": DOOR_CLOSED_SW
            })
        except Exception as e:
            self.log_error("hardware", "Failed to initialize door sensors", {"error": str(e)})
            raise

        # State tracking
        self._expected = None  # "open"|"closed"|None, to better infer opening/closing
        self.last_door_state = 'unknown'
        self.last_light_state = False
        self.last_update = 0

        # Compute initial state
        self.last_door_state = self.get_door_state()
        self.last_light_state = self._read_light_state()

        # Initial publishes for baseline state
        try:
            self.runtime.publish(TOPIC_DOOR_STATUS, self.last_door_state)
            self.runtime.publish(TOPIC_LIGHT_STATUS, 'on' if self.last_light_state else 'off')
        except Exception:
            pass

    def get_door_state(self):
        """Determine current garage door state based on reed switches.

        Returns:
            str: One of "open", "closed", "opening", "closing", or "error".
        """
        open_sw = not self.door_open_sw.value()  # Active low
        closed_sw = not self.door_closed_sw.value()  # Active low

        # Both active is invalid
        if open_sw and closed_sw:
            return 'error'

        # End states
        if open_sw and not closed_sw:
            return 'open'
        if closed_sw and not open_sw:
            return 'closed'

        # Transition: neither switch active
        expected = getattr(self, "_expected", None)
        last = getattr(self, "last_door_state", None)

        # Priority 1: last terminal states
        if last == 'open':
            return 'closing'
        if last == 'closed':
            return 'opening'
        # Priority 2: command hint
        if expected == 'open':
            return 'opening'
        if expected == 'closed':
            return 'closing'
        # Priority 3: keep previous transitional trend
        if last in ('opening',):
            return 'opening'
        if last in ('closing',):
            return 'closing'
        # Default
        return 'closing'

    def toggle_garage_door(self):
        """Momentarily activate the door relay to simulate a wall-button press."""
        self.door_relay.value(1)
        time.sleep(0.5)  # Pulse relay for 500ms
        self.door_relay.value(0)

    def set_light(self, state):
        """Set flood light state and publish status.

        Args:
            state (bool): True to turn on, False to turn off.
        """
        if LIGHT_RELAY_ACTIVE_LOW:
            self.light_relay.value(0 if state else 1)
        else:
            self.light_relay.value(1 if state else 0)
        self.last_light_state = state
        self.runtime.publish(TOPIC_LIGHT_STATUS, 'on' if state else 'off')

    def sos(self, error: str, message: str = "") -> None:
        """Publish an SOS diagnostic event without raising."""
        try:
            payload = {
                "device_id": self.device_id,
                "error": error,
                "message": message,
                "timestamp": time.ticks_ms(),
            }
            try:
                body = json.dumps(payload)
            except Exception:
                body = str(payload)
            self.runtime.publish(self._sos_topic, body)
        except Exception:
            pass

    def mqtt_callback(self, topic, msg):
        """Handle incoming MQTT messages.

        Args:
            topic (str): Topic string.
            msg (bytes|str): Payload.
        """
        try:
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8')
        except Exception:
            pass

        self.log_debug("mqtt", "Received command", {"topic": topic, "message": str(msg)})

        if topic == TOPIC_DOOR_COMMAND and msg in ['open', 'close', 'toggle']:
            if msg == 'open':
                self._expected = 'open'
            elif msg == 'close':
                self._expected = 'closed'
            else:
                self._expected = None
            self.toggle_garage_door()
        elif topic == TOPIC_LIGHT_COMMAND:
            if msg == 'on':
                self.set_light(True)
            elif msg == 'off':
                self.set_light(False)
            elif msg == 'toggle':
                self.set_light(not self.last_light_state)

    def update_sensors(self):
        """Check door state and publish updates."""
        current_time = time.ticks_ms()

        # Update door state if changed
        door_state = self.get_door_state()
        if door_state != self.last_door_state:
            self.runtime.publish(TOPIC_DOOR_STATUS, door_state)
            self.last_door_state = door_state
            if door_state in ('open', 'closed'):
                self._expected = None

        # Publish consolidated status every 30 seconds
        if time.ticks_diff(current_time, self.last_update) > 30000:
            self._publish_status()
            self.last_update = current_time

            # Blink LED to show activity
            try:
                self.led.value(0 if self.led.value() else 1)
            except Exception:
                pass

    def _read_light_state(self):
        """Return True if flood light is currently ON."""
        try:
            v = self.light_relay.value()
        except Exception:
            v = (1 if LIGHT_RELAY_ACTIVE_LOW else 0)
        if LIGHT_RELAY_ACTIVE_LOW:
            return v == 0
        else:
            return v == 1

    def _add_error(self, code: str, message: str):
        """Add an error to the active errors list."""
        for err in self._errors:
            if err["code"] == code:
                return
        self._errors.append({
            "code": code,
            "message": message,
            "since": time.ticks_ms()
        })

    def _clear_error(self, code: str):
        """Remove an error from the active errors list."""
        self._errors = [e for e in self._errors if e["code"] != code]

    def _get_uptime_seconds(self, current_time: int) -> int:
        """Get device uptime in seconds."""
        return time.ticks_diff(current_time, self._boot_time) // 1000

    def _build_status_message(self, current_time: int) -> dict:
        """Build consolidated status message."""
        mem_free = None
        mem_alloc = None
        try:
            mem_free = gc.mem_free()
            mem_alloc = gc.mem_alloc()
        except Exception:
            pass

        status = {
            "timestamp": current_time,
            "uptime_s": self._get_uptime_seconds(current_time),
            "health": "online",
            "door": {
                "state": self.last_door_state
            },
            "light": {
                "state": "on" if self.last_light_state else "off"
            },
            "errors": self._errors if self._errors else [],
            "memory": {
                "free": mem_free,
                "allocated": mem_alloc
            }
        }

        if self._errors:
            status["health"] = "degraded"

        return status

    def _publish_status(self):
        """Publish consolidated status message."""
        current_time = time.ticks_ms()
        status = self._build_status_message(current_time)

        try:
            payload = json.dumps(status)
            self.runtime.publish(TOPIC_STATUS, payload)
            self.log_debug("mqtt", "Published consolidated status", {"size": len(payload)})
        except Exception as e:
            self.log_error("mqtt", "Failed to publish status", {"error": str(e)})

    # Logging helper methods
    def log_debug(self, component: str, message: str, details: dict = None):
        if self.logger:
            self.logger.debug(component, message, details)

    def log_info(self, component: str, message: str, details: dict = None):
        if self.logger:
            self.logger.info(component, message, details)

    def log_warning(self, component: str, message: str, details: dict = None):
        if self.logger:
            self.logger.warning(component, message, details)

    def log_error(self, component: str, message: str, details: dict = None, immediate: bool = True):
        if self.logger:
            self.logger.error(component, message, details, immediate)


_controller = None
_runtime = None


def init(runtime):
    """Initialize the app with the bootstrap-provided runtime."""
    global _controller, _runtime
    _runtime = runtime
    cfg = load_device_config()
    device_id = cfg.get("device_id") or "garage-controller"
    try:
        print("[APP] init controller...")
    except Exception:
        pass
    _controller = GarageController(runtime, device_id)
    try:
        print("[APP] controller ready")
    except Exception:
        pass
    # Subscribe to command topics
    try:
        runtime.subscribe(TOPIC_DOOR_COMMAND, lambda t, m: _controller.mqtt_callback(t, m), fast=True)
        runtime.subscribe(TOPIC_LIGHT_COMMAND, lambda t, m: _controller.mqtt_callback(t, m), fast=True)
    except Exception:
        pass


def tick():
    """Periodic work slice. Must return quickly."""
    global _controller
    if _controller:
        _controller.update_sensors()
        # Periodic garbage collection every 10 minutes
        current_time = time.ticks_ms()
        if not hasattr(_controller, '_last_gc_ms'):
            _controller._last_gc_ms = current_time
        if time.ticks_diff(current_time, _controller._last_gc_ms) > 600000:
            try:
                gc.collect()
                _controller._last_gc_ms = current_time
            except Exception:
                pass


def shutdown(reason=""):
    """Best-effort quiesce before OTA/reset."""
    global _runtime
    try:
        if _runtime:
            _runtime.unsubscribe(TOPIC_DOOR_COMMAND)
            _runtime.unsubscribe(TOPIC_LIGHT_COMMAND)
    except Exception:
        pass
