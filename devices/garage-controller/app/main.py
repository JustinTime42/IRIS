# MicroPython placeholder app for garage-controller
# Reason: Provide a simple visible heartbeat to validate bootstrap handoff and app execution.

import time
from machine import Pin


def main():
    """
    Blink the onboard LED once per second indefinitely.

    This serves as a minimal placeholder app to verify that the bootstrap layer
    can hand off to the application and that the device is responsive.

    Returns:
        None
    """
    try:
        led = Pin("LED", Pin.OUT)
    except Exception:
        # Fallback for boards where "LED" alias is unavailable.
        # On Raspberry Pi Pico (non-W), the onboard LED is typically on GP25.
        led = Pin(25, Pin.OUT)

    state = 0
    while True:
        state ^= 1
        try:
            led.value(state)
        except Exception:
            pass
        time.sleep(1)
