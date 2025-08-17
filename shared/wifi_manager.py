"""
WiFi management utilities for MicroPython on Pico W.

Provides simple connect/disconnect helpers with retry and status checks.
"""
# Reason: Centralize WiFi logic for reuse by bootstrap and app layers.

try:
    import network  # type: ignore
except Exception:
    network = None  # type: ignore
import time


def is_connected() -> bool:
    """
    Check if the station interface is connected.

    Returns:
        bool: True if connected, False otherwise.
    """
    if not network:
        return False
    try:
        sta = network.WLAN(network.STA_IF)
        return bool(sta.isconnected())
    except Exception:
        return False


def connect(ssid: str, password: str, timeout_ms: int = 15000, retry_delay_ms: int = 500) -> bool:
    """
    Connect to WiFi with a timeout and basic retry loop.

    Args:
        ssid (str): WiFi network SSID.
        password (str): WiFi password.
        timeout_ms (int): Overall timeout in milliseconds.
        retry_delay_ms (int): Delay between attempts in milliseconds.

    Returns:
        bool: True if connected, False otherwise.
    """
    if not network:
        return False
    sta = network.WLAN(network.STA_IF)
    try:
        if not sta.active():
            sta.active(True)
        if sta.isconnected():
            return True
        start = time.ticks_ms()
        sta.connect(ssid, password)
        while not sta.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                break
            time.sleep_ms(retry_delay_ms)
        return bool(sta.isconnected())
    except Exception:
        return False


def disconnect() -> None:
    """
    Disconnect from WiFi gracefully.

    Returns:
        None
    """
    if not network:
        return
    try:
        sta = network.WLAN(network.STA_IF)
        if sta.isconnected():
            sta.disconnect()
    except Exception:
        pass
