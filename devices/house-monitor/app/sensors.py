"""
Sensor scaffolding for the house-monitor Pico W.

Provides placeholders for:
- DS18B20 temperature sensor (freezer)
- Reed switch (freezer door)

Note: Implement with MicroPython `machine`, `onewire`, `ds18x20` when wiring is finalized.
"""

# Reason: Separate hardware logic from the main loop for clarity and testability.


def read_freezer_temperature_f() -> float | None:
    """Read freezer temperature in Fahrenheit.

    Returns:
        float | None: Temperature in °F if available, otherwise None.
    """
    # TODO: Implement using DS18B20 via onewire + ds18x20 modules.
    # TODO: Convert from °C to °F.
    return None


def read_door_status() -> str:
    """Read freezer door status via reed switch.

    Returns:
        str: "open" or "closed".
    """
    # TODO: Implement using machine.Pin with pull-up and debounce.
    return "closed"
