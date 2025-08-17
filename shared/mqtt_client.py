"""
Basic MQTT client wrapper for MicroPython (Pico W).

Provides a thin abstraction around `umqtt.simple` with reconnect logic hooks.
This is a shared component used by both bootstrap and application layers.
"""
# Reason: Keep a unified MQTT interface across devices; simplify imports and testing.

try:
    from umqtt.simple import MQTTClient  # type: ignore
except Exception:
    MQTTClient = None  # type: ignore

import ubinascii  # type: ignore
import machine  # type: ignore
import time
from typing import Callable, Optional


class Mqtt:
    """
    Minimal MQTT helper.

    Attributes:
        client (MQTTClient | None): Underlying MQTT client instance.
        client_id (bytes): Unique client id.
        on_message (Optional[Callable[[str, bytes], None]]): Callback for messages.
    """

    def __init__(self, host: str, port: int = 1883, user: Optional[str] = None, password: Optional[str] = None, keepalive: int = 30):
        """
        Initialize MQTT client with safe defaults.

        Args:
            host (str): MQTT broker host.
            port (int): Broker port.
            user (Optional[str]): Username.
            password (Optional[str]): Password.
            keepalive (int): Keepalive seconds.
        """
        self.client = None
        self.client_id = ubinascii.hexlify(machine.unique_id()) if hasattr(machine, "unique_id") else b"pico"
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive
        self.on_message: Optional[Callable[[str, bytes], None]] = None
        self._lwt: Optional[tuple[str, str, bool, int]] = None  # (topic, msg, retain, qos)

    def connect(self) -> bool:
        """
        Connect to the broker. Returns True on success.
        """
        if MQTTClient is None:
            return False
        try:
            self.client = MQTTClient(self.client_id, self.host, self.port, self.user, self.password, keepalive=self.keepalive)
            # Configure last will before connecting if provided
            try:
                if self._lwt:
                    t, m, r, q = self._lwt
                    self.client.set_last_will(t.encode(), m.encode(), r, q)  # type: ignore
            except Exception:
                pass
            if self.on_message:
                self.client.set_callback(self._dispatch)  # type: ignore
            self.client.connect()
            return True
        except Exception:
            self.client = None
            return False

    def disconnect(self) -> None:
        """
        Disconnect from the broker if connected.
        """
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass
        finally:
            self.client = None

    def subscribe(self, topic: str) -> bool:
        """
        Subscribe to a topic.
        """
        try:
            if not self.client:
                return False
            self.client.subscribe(topic.encode())  # type: ignore
            return True
        except Exception:
            return False

    def publish(self, topic: str, msg: str | bytes, retain: bool = False, qos: int = 0) -> bool:
        """
        Publish a message to a topic.
        """
        try:
            if not self.client:
                return False
            payload = msg if isinstance(msg, bytes) else msg.encode()
            # umqtt.simple doesn't expose qos/retain in all ports; best-effort
            self.client.publish(topic.encode(), payload)  # type: ignore
            return True
        except Exception:
            return False

    def check_msg(self) -> None:
        """
        Non-blocking check for incoming messages.
        """
        try:
            if self.client:
                self.client.check_msg()  # type: ignore
        except Exception:
            # Allow caller to handle reconnect if desired
            pass

    def wait_msg(self) -> None:
        """
        Blocking wait for a single message.
        """
        try:
            if self.client:
                self.client.wait_msg()  # type: ignore
        except Exception:
            pass

    def set_message_handler(self, handler: Callable[[str, bytes], None]) -> None:
        """
        Set the message handler callback.
        """
        self.on_message = handler
        if self.client:
            try:
                self.client.set_callback(self._dispatch)  # type: ignore
            except Exception:
                pass

    def set_last_will(self, topic: str, msg: str, retain: bool = False, qos: int = 0) -> None:
        """
        Configure MQTT Last Will (LWT) published by broker if we disconnect ungracefully.

        Args:
            topic (str): LWT topic.
            msg (str): LWT message.
            retain (bool): Retain flag.
            qos (int): QoS level.
        """
        self._lwt = (topic, msg, retain, qos)

    # ------------------------------------------------------------------
    def _dispatch(self, topic: bytes, msg: bytes) -> None:
        try:
            if self.on_message:
                self.on_message(topic.decode(), msg)
        except Exception:
            # Swallow to avoid crashing networking stack
            pass
