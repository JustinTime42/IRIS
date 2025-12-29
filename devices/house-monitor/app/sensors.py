"""
Sensor utilities for the house-monitor Pico W.

Provides helper classes and functions for:
- DS18B20 temperature sensor (freezer)
- Reed switch (door detection)
- City power detection

These utilities are designed to be non-blocking and suitable for
cooperative multitasking in the tick() loop.
"""

import time

try:
    from machine import Pin
except ImportError:
    Pin = None  # type: ignore

try:
    import onewire
    import ds18x20
    HAS_ONEWIRE = True
except ImportError:
    HAS_ONEWIRE = False
    onewire = None  # type: ignore
    ds18x20 = None  # type: ignore


class DS18B20Sensor:
    """Non-blocking DS18B20 temperature sensor driver.
    
    Supports async temperature conversion to avoid blocking the main loop
    for the 750ms conversion time.
    
    Usage:
        sensor = DS18B20Sensor(pin_num=4)
        
        # In tick loop:
        if sensor.should_start_read(current_time, interval_ms=30000):
            sensor.start_conversion()
        
        if sensor.is_conversion_complete(current_time):
            temp_f = sensor.read_temperature_f()
            if temp_f is not None:
                # Use temperature
    
    Attributes:
        pin_num (int): GPIO pin number for 1-Wire data.
        sensor (ds18x20.DS18X20|None): DS18B20 driver instance.
        roms (list): List of discovered sensor ROM addresses.
        initialized (bool): True if sensor is ready for use.
    """
    
    CONVERSION_TIME_MS = 800  # 750ms typical + margin
    
    def __init__(self, pin_num: int):
        """Initialize DS18B20 sensor.
        
        Args:
            pin_num: GPIO pin number for 1-Wire data line.
        """
        self.pin_num = pin_num
        self.sensor = None
        self.roms = []
        self.last_read_time = 0
        self.conversion_start = 0
        self.converting = False
        self.initialized = False
        
        self._init_sensor()
    
    def _init_sensor(self):
        """Initialize the sensor hardware."""
        if not HAS_ONEWIRE or not Pin:
            return
        
        try:
            pin = Pin(self.pin_num)
            ow = onewire.OneWire(pin)
            self.sensor = ds18x20.DS18X20(ow)
            self.roms = self.sensor.scan()
            self.initialized = len(self.roms) > 0
        except Exception:
            self.initialized = False
    
    def is_available(self) -> bool:
        """Check if sensor is available and initialized.
        
        Returns:
            bool: True if sensor is ready for use.
        """
        return self.initialized and len(self.roms) > 0
    
    def should_start_read(self, current_time: int, interval_ms: int = 30000) -> bool:
        """Check if it's time to start a new temperature read.
        
        Args:
            current_time: Current time in ticks_ms.
            interval_ms: Minimum interval between reads.
            
        Returns:
            bool: True if a new read should be started.
        """
        if not self.is_available():
            return False
        if self.converting:
            return False
        return time.ticks_diff(current_time, self.last_read_time) >= interval_ms
    
    def start_conversion(self) -> bool:
        """Start async temperature conversion.
        
        Returns:
            bool: True if conversion started successfully.
        """
        if not self.is_available():
            return False
        
        try:
            self.sensor.convert_temp()
            self.conversion_start = time.ticks_ms()
            self.converting = True
            return True
        except Exception:
            return False
    
    def is_conversion_complete(self, current_time: int) -> bool:
        """Check if conversion is complete.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            bool: True if conversion is complete and result can be read.
        """
        if not self.converting:
            return False
        return time.ticks_diff(current_time, self.conversion_start) >= self.CONVERSION_TIME_MS
    
    def read_temperature_f(self):
        """Read temperature in Fahrenheit after conversion.
        
        Returns:
            float|None: Temperature in Fahrenheit, or None on error.
        """
        if not self.is_available():
            return None
        
        self.converting = False
        self.last_read_time = time.ticks_ms()
        
        try:
            temp_c = self.sensor.read_temp(self.roms[0])
            return temp_c * 1.8 + 32
        except Exception:
            return None
    
    def read_temperature_c(self):
        """Read temperature in Celsius after conversion.
        
        Returns:
            float|None: Temperature in Celsius, or None on error.
        """
        if not self.is_available():
            return None
        
        self.converting = False
        self.last_read_time = time.ticks_ms()
        
        try:
            return self.sensor.read_temp(self.roms[0])
        except Exception:
            return None
    
    def get_rom_ids(self) -> list:
        """Get list of ROM IDs as hex strings.
        
        Returns:
            list: List of ROM ID strings in format "xx:xx:xx:xx:xx:xx:xx:xx".
        """
        return [":".join(["{:02x}".format(b) for b in rom]) for rom in self.roms]


class ReedSwitch:
    """Debounced reed switch driver for door detection.
    
    Usage:
        switch = ReedSwitch(pin_num=3, active_low=True)
        
        # In tick loop:
        state = switch.read_debounced(current_time)
        if state is not None and state != last_state:
            # State changed
    
    Attributes:
        pin (machine.Pin): GPIO pin instance.
        debounce_ms (int): Debounce time in milliseconds.
        active_low (bool): True if switch closure pulls pin LOW.
    """
    
    def __init__(self, pin_num: int, debounce_ms: int = 50, active_low: bool = True):
        """Initialize reed switch.
        
        Args:
            pin_num: GPIO pin number.
            debounce_ms: Debounce time in milliseconds.
            active_low: If True, switch closure pulls pin LOW.
        """
        if Pin:
            self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        else:
            self.pin = None
        self.debounce_ms = debounce_ms
        self.active_low = active_low
        
        self.debounce_start = 0
        self.debounce_value = None
        self.stable_state = None
    
    def read_raw(self) -> bool:
        """Read raw switch state.
        
        Returns:
            bool: True if switch is closed (activated).
        """
        if not self.pin:
            return False
        value = self.pin.value()
        if self.active_low:
            return value == 0  # Closed = LOW
        else:
            return value == 1  # Closed = HIGH
    
    def read_debounced(self, current_time: int):
        """Read debounced switch state.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            bool|None: Debounced state if stable, None if still bouncing.
        """
        raw = self.read_raw()
        
        if raw != self.debounce_value:
            # Value changed, restart debounce timer
            self.debounce_value = raw
            self.debounce_start = current_time
            return None
        
        # Check if stable long enough
        if time.ticks_diff(current_time, self.debounce_start) >= self.debounce_ms:
            self.stable_state = raw
            return raw
        
        return None
    
    def get_stable_state(self):
        """Get last known stable state.
        
        Returns:
            bool|None: Last stable state or None if never stable.
        """
        return self.stable_state


class DoorMonitor:
    """Door monitoring with ajar timing.
    
    Combines reed switch reading with ajar duration tracking.
    
    Usage:
        door = DoorMonitor(pin_num=3)
        
        # In tick loop:
        status, ajar_secs = door.update(current_time)
        if status is not None:
            # Status changed or ajar time updated
    
    Attributes:
        switch (ReedSwitch): Underlying reed switch driver.
        last_status (str|None): Last known door status.
        opened_at (int|None): Timestamp when door was opened.
    """
    
    def __init__(self, pin_num: int, debounce_ms: int = 50):
        """Initialize door monitor.
        
        Args:
            pin_num: GPIO pin for reed switch.
            debounce_ms: Debounce time in milliseconds.
        """
        self.switch = ReedSwitch(pin_num, debounce_ms, active_low=True)
        self.last_status = None
        self.opened_at = None
    
    def update(self, current_time: int) -> tuple:
        """Update door state and timing.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            tuple: (status_str, ajar_seconds) where:
                - status_str is "open", "closed", or None if unchanged
                - ajar_seconds is time door has been open (0 if closed)
        """
        is_closed = self.switch.read_debounced(current_time)
        
        status = None
        ajar_secs = 0
        
        if is_closed is not None:
            current_status = "closed" if is_closed else "open"
            
            if current_status != self.last_status:
                status = current_status
                self.last_status = current_status
                
                if current_status == "open":
                    self.opened_at = current_time
                else:
                    self.opened_at = None
            
            if current_status == "open" and self.opened_at is not None:
                ajar_secs = time.ticks_diff(current_time, self.opened_at) // 1000
        
        return status, ajar_secs
    
    def get_status(self) -> str:
        """Get current door status.
        
        Returns:
            str: "open", "closed", or "unknown".
        """
        return self.last_status or "unknown"
    
    def get_ajar_seconds(self, current_time: int) -> int:
        """Get current ajar duration in seconds.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            int: Seconds door has been open, or 0 if closed.
        """
        if self.last_status == "open" and self.opened_at is not None:
            return time.ticks_diff(current_time, self.opened_at) // 1000
        return 0


class PowerMonitor:
    """City power presence monitor.
    
    Monitors a GPIO input connected to an indicator of city/utility power
    presence (e.g., output from an RS-25-5 power supply on the utility side
    of a transfer switch).
    
    Usage:
        power = PowerMonitor(pin_num=2)
        
        # In tick loop:
        status = power.update(current_time)
        if status is not None:
            # Status changed
    
    Attributes:
        pin (machine.Pin): GPIO pin instance.
        debounce_ms (int): Debounce time in milliseconds.
        last_status (str|None): Last known power status.
    """
    
    def __init__(self, pin_num: int, debounce_ms: int = 100):
        """Initialize power monitor.
        
        Args:
            pin_num: GPIO pin connected to city power indicator.
            debounce_ms: Debounce time (longer for power to filter noise).
        """
        if Pin:
            # Pull-down so floating = offline (fail-safe)
            self.pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
        else:
            self.pin = None
        self.debounce_ms = debounce_ms
        
        self.debounce_start = 0
        self.debounce_value = None
        self.last_status = None
    
    def read_raw(self) -> str:
        """Read raw power state.
        
        Returns:
            str: "online" if power present, "offline" otherwise.
        """
        if not self.pin:
            return "offline"
        return "online" if self.pin.value() else "offline"
    
    def update(self, current_time: int):
        """Update power state with debouncing.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            str|None: New status if changed, None if unchanged or debouncing.
        """
        raw = self.read_raw()
        
        if raw != self.debounce_value:
            self.debounce_value = raw
            self.debounce_start = current_time
            return None
        
        if time.ticks_diff(current_time, self.debounce_start) >= self.debounce_ms:
            if raw != self.last_status:
                self.last_status = raw
                return raw
        
        return None
    
    def get_status(self) -> str:
        """Get current power status.
        
        Returns:
            str: "online", "offline", or "unknown".
        """
        return self.last_status or "unknown"


# Utility functions for direct sensor access (simpler use cases)

def read_freezer_temperature_f(pin_num: int = 4):
    """Read freezer temperature in Fahrenheit (blocking).
    
    Note: This blocks for ~750ms for DS18B20 conversion.
    For non-blocking operation, use DS18B20Sensor class.
    
    Args:
        pin_num: GPIO pin for DS18B20 data line.
        
    Returns:
        float|None: Temperature in Fahrenheit, or None on error.
    """
    if not HAS_ONEWIRE or not Pin:
        return None
    
    try:
        pin = Pin(pin_num)
        ow = onewire.OneWire(pin)
        ds = ds18x20.DS18X20(ow)
        roms = ds.scan()
        
        if not roms:
            return None
        
        ds.convert_temp()
        time.sleep_ms(750)
        
        temp_c = ds.read_temp(roms[0])
        return temp_c * 1.8 + 32
        
    except Exception:
        return None


def read_door_status(pin_num: int = 3) -> str:
    """Read freezer door status (instant, no debounce).
    
    Args:
        pin_num: GPIO pin for reed switch.
        
    Returns:
        str: "open" or "closed".
    """
    if not Pin:
        return "closed"
    
    try:
        pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        # LOW = closed (switch activated), HIGH = open
        return "closed" if not pin.value() else "open"
    except Exception:
        return "closed"


def read_power_status(pin_num: int = 2) -> str:
    """Read city power status (instant, no debounce).
    
    Args:
        pin_num: GPIO pin for power indicator.
        
    Returns:
        str: "online" or "offline".
    """
    if not Pin:
        return "offline"
    
    try:
        pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
        return "online" if pin.value() else "offline"
    except Exception:
        return "offline"
