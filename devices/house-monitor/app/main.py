"""
House Monitor Pico W Application

Monitors:
- City power status (GPIO input from RS-25-5 PSU)
- Freezer temperature (DS18B20)
- Freezer door ajar detection (reed switch)

Publishes consolidated status every 30 seconds to single topic:
  home/house-monitor/status

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
    from machine import Pin
except Exception:
    import sys as machine  # type: ignore
    Pin = None  # type: ignore

try:
    import onewire
    import ds18x20
    HAS_ONEWIRE = True
except ImportError:
    HAS_ONEWIRE = False
    onewire = None  # type: ignore
    ds18x20 = None  # type: ignore

try:
    import ujson as json  # type: ignore
except ImportError:
    import json  # type: ignore

from shared.config_manager import load_device_config
from shared.device_logger import DeviceLogger, set_global_logger

# Pin Definitions
CITY_POWER_PIN = 2      # Input: HIGH = city power present
DOOR_REED_PIN = 3       # Input: LOW = door closed (with internal pull-up)
DS18B20_PIN = 4         # 1-Wire: Temperature sensor
LED_PIN = 'LED'         # Built-in LED for status

# MQTT Topics - Consolidated approach
TOPIC_STATUS = 'home/house-monitor/status'  # Single consolidated status message

# Timing constants
STATUS_INTERVAL_MS = 30000          # Publish consolidated status every 30 seconds
DS18B20_CONVERSION_MS = 800         # DS18B20 conversion time + margin
DOOR_DEBOUNCE_MS = 50               # Door switch debounce
POWER_DEBOUNCE_MS = 100             # Power input debounce


class HouseMonitor:
    """Main controller for house monitoring functions.
    
    Publishes a single consolidated status message every 30 seconds containing
    all sensor readings, health status, and any active errors.
    
    Attributes:
        runtime: Bootstrap-provided runtime with publish/subscribe/sos APIs.
        device_id (str): Device ID from config.
        led (machine.Pin): Built-in LED pin for heartbeat.
        power_pin (machine.Pin): Input for city power detection.
        door_pin (machine.Pin): Input for door reed switch.
        ds_sensor (ds18x20.DS18X20|None): DS18B20 bus instance if available.
        ds_roms (list): Discovered DS18B20 ROMs.
    """
    
    def __init__(self, runtime, device_id: str):
        """Initialize hardware and state.
        
        Args:
            runtime: Bootstrap-provided runtime with publish/subscribe/sos APIs.
            device_id: Device identifier from config.
        """
        self.runtime = runtime
        self.device_id = device_id
        self._boot_time = time.ticks_ms()
        
        # Initialize logger
        try:
            self.logger = DeviceLogger(runtime, device_id, min_level='INFO')
            set_global_logger(self.logger)
            self.logger.info("app", "House monitor initializing", {
                "version": "1.0.0",
                "features": ["city_power", "freezer_temp", "door_monitor"],
                "pin_config": {
                    "city_power": CITY_POWER_PIN,
                    "door_reed": DOOR_REED_PIN,
                    "ds18b20": DS18B20_PIN
                }
            })
        except Exception as e:
            print("[ERROR] Failed to initialize logger: {}".format(e))
            self.logger = None
        
        # Active errors list
        self._errors = []
        
        # Initialize LED
        self.led = None
        try:
            if Pin:
                self.led = Pin(LED_PIN, Pin.OUT)
                self.led.value(0)
                self.log_info("hardware", "LED initialized", {"pin": LED_PIN})
        except Exception as e:
            self.log_error("hardware", "Failed to initialize LED", {"error": str(e)})
        
        # Initialize city power input
        self.power_pin = None
        try:
            if Pin:
                # Using pull-down so floating reads LOW (fail-safe: assume power out if disconnected)
                self.power_pin = Pin(CITY_POWER_PIN, Pin.IN, Pin.PULL_DOWN)
                self.log_info("hardware", "City power pin initialized", {"pin": CITY_POWER_PIN})
        except Exception as e:
            self.log_error("hardware", "Failed to initialize city power pin", {"error": str(e)})
            self._add_error("power_pin_init_failed", str(e))
        
        # Initialize door reed switch
        self.door_pin = None
        try:
            if Pin:
                self.door_pin = Pin(DOOR_REED_PIN, Pin.IN, Pin.PULL_UP)
                self.log_info("hardware", "Door reed switch initialized", {"pin": DOOR_REED_PIN})
        except Exception as e:
            self.log_error("hardware", "Failed to initialize door pin", {"error": str(e)})
            self._add_error("door_pin_init_failed", str(e))
        
        # Initialize DS18B20
        self.ds_sensor = None
        self.ds_roms = []
        if HAS_ONEWIRE and Pin:
            try:
                ds_pin = Pin(DS18B20_PIN)
                self.ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
                self.ds_roms = self.ds_sensor.scan()
                self.log_info("sensors", "DS18B20 initialized", {
                    "pin": DS18B20_PIN,
                    "devices_found": len(self.ds_roms),
                    "roms": [":".join(["{:02x}".format(b) for b in rom]) for rom in self.ds_roms]
                })
                if not self.ds_roms:
                    self._add_error("ds18b20_not_found", "No DS18B20 sensors found on bus")
            except Exception as e:
                self.log_error("sensors", "DS18B20 initialization failed", {"error": str(e)})
                self._add_error("ds18b20_init_failed", str(e))
        else:
            self.log_warning("sensors", "OneWire not available", {"has_onewire": HAS_ONEWIRE})
        
        # State tracking (for change detection in logs, not for separate publishing)
        self.last_power_state = None
        self.last_door_state = None
        self.door_opened_at = None
        self.last_temp_f = None
        
        # Debounce state
        self.power_debounce_start = 0
        self.power_debounce_value = None
        self.power_stable_state = None
        self.door_debounce_start = 0
        self.door_debounce_value = None
        self.door_stable_state = None
        
        # Timing state
        self.last_status_publish = 0
        
        # Async temperature reading state
        self.temp_conversion_started = 0
        self.temp_converting = False
        self.temp_ready = False
        self.pending_temp_f = None
        
        # Initialize stable states
        self._init_stable_states()
        
        # Publish initial status immediately
        self._publish_status()
    
    def _init_stable_states(self):
        """Initialize debounced stable states on startup."""
        current_time = time.ticks_ms()
        
        # Power state
        power_raw = self._read_power_raw()
        self.power_debounce_value = power_raw
        self.power_debounce_start = current_time
        self.power_stable_state = power_raw
        self.last_power_state = power_raw
        
        # Door state
        door_raw = self._read_door_raw()
        self.door_debounce_value = door_raw
        self.door_debounce_start = current_time
        self.door_stable_state = door_raw
        self.last_door_state = door_raw
        if door_raw == "open":
            self.door_opened_at = current_time
    
    def _add_error(self, code: str, message: str):
        """Add an error to the active errors list.
        
        Args:
            code: Error code/type.
            message: Human-readable details.
        """
        # Check if error already exists
        for err in self._errors:
            if err["code"] == code:
                return  # Already tracked
        
        self._errors.append({
            "code": code,
            "message": message,
            "since": time.ticks_ms()
        })
    
    def _clear_error(self, code: str):
        """Remove an error from the active errors list.
        
        Args:
            code: Error code to clear.
        """
        self._errors = [e for e in self._errors if e["code"] != code]
    
    def _read_power_raw(self) -> str:
        """Read city power state directly (no debounce).
        
        Returns:
            str: "online" if power present, "offline" otherwise.
        """
        if not self.power_pin:
            return "offline"  # Fail-safe
        # HIGH = power present, LOW = power out
        return "online" if self.power_pin.value() else "offline"
    
    def _read_door_raw(self) -> str:
        """Read door state directly (no debounce).
        
        Returns:
            str: "closed" if door closed, "open" otherwise.
        """
        if not self.door_pin:
            return "closed"  # Fail-safe
        # LOW = closed (switch activated by magnet), HIGH = open
        return "closed" if not self.door_pin.value() else "open"
    
    def _update_power_state(self, current_time: int):
        """Update debounced power state.
        
        Args:
            current_time: Current time in ticks_ms.
        """
        raw = self._read_power_raw()
        
        if raw != self.power_debounce_value:
            self.power_debounce_value = raw
            self.power_debounce_start = current_time
            return
        
        if time.ticks_diff(current_time, self.power_debounce_start) >= POWER_DEBOUNCE_MS:
            if raw != self.power_stable_state:
                self.log_info("power", "City power state changed", {
                    "old_state": self.power_stable_state,
                    "new_state": raw
                })
                self.power_stable_state = raw
    
    def _update_door_state(self, current_time: int):
        """Update debounced door state.
        
        Args:
            current_time: Current time in ticks_ms.
        """
        raw = self._read_door_raw()
        
        if raw != self.door_debounce_value:
            self.door_debounce_value = raw
            self.door_debounce_start = current_time
            return
        
        if time.ticks_diff(current_time, self.door_debounce_start) >= DOOR_DEBOUNCE_MS:
            if raw != self.door_stable_state:
                self.log_info("door", "Door state changed", {
                    "old_state": self.door_stable_state,
                    "new_state": raw
                })
                self.door_stable_state = raw
                
                if raw == "open":
                    self.door_opened_at = current_time
                else:
                    self.door_opened_at = None
    
    def _update_temperature(self, current_time: int):
        """Update temperature reading (non-blocking).
        
        Manages the async conversion cycle. Temperature is read once
        per status publish cycle.
        
        Args:
            current_time: Current time in ticks_ms.
        """
        if not self.ds_sensor or not self.ds_roms:
            return
        
        # Start conversion if not already in progress
        if not self.temp_converting and not self.temp_ready:
            try:
                self.ds_sensor.convert_temp()
                self.temp_conversion_started = current_time
                self.temp_converting = True
            except Exception as e:
                self.log_error("sensors", "Failed to start temp conversion", {"error": str(e)})
                self._add_error("ds18b20_read_error", str(e))
                return
        
        # Check if conversion is complete
        if self.temp_converting:
            if time.ticks_diff(current_time, self.temp_conversion_started) >= DS18B20_CONVERSION_MS:
                self.temp_converting = False
                try:
                    temp_c = self.ds_sensor.read_temp(self.ds_roms[0])
                    temp_f = temp_c * 1.8 + 32
                    
                    # Validate temperature
                    if -50.0 <= temp_f <= 50.0:
                        self.pending_temp_f = temp_f
                        self.last_temp_f = temp_f
                        self.temp_ready = True
                        self._clear_error("ds18b20_read_error")
                        self._clear_error("temp_out_of_range")
                    else:
                        self._add_error("temp_out_of_range", 
                            "Temperature {:.1f}F outside valid range".format(temp_f))
                        self.pending_temp_f = None
                        self.temp_ready = True
                except Exception as e:
                    self.log_error("sensors", "Failed to read temperature", {"error": str(e)})
                    self._add_error("ds18b20_read_error", str(e))
                    self.pending_temp_f = None
                    self.temp_ready = True
    
    def _get_door_ajar_seconds(self, current_time: int) -> int:
        """Get door ajar duration in seconds.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            int: Seconds door has been open, or 0 if closed.
        """
        if self.door_stable_state == "open" and self.door_opened_at is not None:
            return time.ticks_diff(current_time, self.door_opened_at) // 1000
        return 0
    
    def _get_uptime_seconds(self, current_time: int) -> int:
        """Get device uptime in seconds.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            int: Uptime in seconds.
        """
        return time.ticks_diff(current_time, self._boot_time) // 1000
    
    def _build_status_message(self, current_time: int) -> dict:
        """Build consolidated status message.
        
        Args:
            current_time: Current time in ticks_ms.
            
        Returns:
            dict: Status message payload.
        """
        # Get memory stats
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
            "power": {
                "city": self.power_stable_state or "unknown"
            },
            "freezer": {
                "temperature_f": self.pending_temp_f,
                "door": self.door_stable_state or "unknown",
                "door_ajar_s": self._get_door_ajar_seconds(current_time)
            },
            "errors": self._errors if self._errors else [],
            "memory": {
                "free": mem_free,
                "allocated": mem_alloc
            }
        }
        
        # Set health based on errors
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
            self.log_debug("mqtt", "Published status", {"size": len(payload)})
        except Exception as e:
            self.log_error("mqtt", "Failed to publish status", {"error": str(e)})
        
        # Reset temperature ready flag for next cycle
        self.temp_ready = False
        self.pending_temp_f = self.last_temp_f  # Keep last known value
        
        # Toggle LED on status publish
        if self.led:
            try:
                self.led.value(0 if self.led.value() else 1)
            except Exception:
                pass
        
        # Periodic garbage collection
        try:
            gc.collect()
        except Exception:
            pass
    
    def update(self):
        """Main update loop - called frequently from tick()."""
        current_time = time.ticks_ms()
        
        # Update sensor states (debouncing, async reads)
        self._update_power_state(current_time)
        self._update_door_state(current_time)
        self._update_temperature(current_time)
        
        # Publish consolidated status every 30 seconds
        if time.ticks_diff(current_time, self.last_status_publish) >= STATUS_INTERVAL_MS:
            # Wait for temperature to be ready if conversion is in progress
            # (small delay is fine, don't block indefinitely)
            if not self.temp_converting or self.temp_ready:
                self._publish_status()
                self.last_status_publish = current_time
    
    # Logging helper methods
    def log_debug(self, component: str, message: str, details: dict = None):
        """Log debug message."""
        if self.logger:
            self.logger.debug(component, message, details)
    
    def log_info(self, component: str, message: str, details: dict = None):
        """Log info message."""
        if self.logger:
            self.logger.info(component, message, details)
    
    def log_warning(self, component: str, message: str, details: dict = None):
        """Log warning message."""
        if self.logger:
            self.logger.warning(component, message, details)
    
    def log_error(self, component: str, message: str, details: dict = None, immediate: bool = True):
        """Log error message."""
        if self.logger:
            self.logger.error(component, message, details, immediate)


# Module-level state
_monitor = None
_runtime = None


def init(runtime):
    """Initialize the app with the bootstrap-provided runtime.
    
    Args:
        runtime: Runtime API from bootstrap (publish/subscribe/sos/etc.).
    """
    global _monitor, _runtime
    _runtime = runtime
    
    cfg = load_device_config()
    device_id = cfg.get("device_id") or "house-monitor"
    
    try:
        print("[APP] Initializing house-monitor as {}".format(device_id))
    except Exception:
        pass
    
    _monitor = HouseMonitor(runtime, device_id)
    
    try:
        print("[APP] House monitor ready")
    except Exception:
        pass


def tick():
    """Periodic work slice. Must return quickly."""
    global _monitor
    if _monitor:
        _monitor.update()


def shutdown(reason=""):
    """Cleanup before OTA or reset.
    
    Args:
        reason: Reason for shutdown (e.g., 'update').
    """
    global _monitor
    if _monitor and _monitor.logger:
        _monitor.log_info("app", "Shutting down", {"reason": reason})
        _monitor.logger.flush()
