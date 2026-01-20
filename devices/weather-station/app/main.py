"""
Weather Station Pico W Application

Monitors:
- Outdoor temperature (DS18B20 on GP7) - primary weather temp
- Weather pressure (BMP388 on I2C0: SDA=GP4, SCL=GP5)

Publishes individual topics:
  home/weather-station/weather/temperature  (DS18B20 outdoor)
  home/weather-station/weather/pressure     (BMP388)

Publishes consolidated status every 30 seconds:
  home/weather-station/status (includes BMP388 temp for reference)

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
    from machine import Pin, I2C
except Exception:
    import sys as machine  # type: ignore
    Pin = None  # type: ignore
    I2C = None  # type: ignore

try:
    import onewire
    import ds18x20
    HAS_ONEWIRE = True
except ImportError:
    HAS_ONEWIRE = False
    onewire = None  # type: ignore
    ds18x20 = None  # type: ignore

try:
    import bmp3xx
    HAS_BMP3XX = True
except ImportError:
    HAS_BMP3XX = False
    bmp3xx = None  # type: ignore

try:
    import ujson as json  # type: ignore
except ImportError:
    import json  # type: ignore

from shared.config_manager import load_device_config
from shared.device_logger import DeviceLogger, set_global_logger

# Pin Definitions
DS18B20_OUTDOOR_PIN = 7   # 1-Wire: Outdoor temperature sensor (primary weather temp)
I2C_SDA = 4               # I2C0 SDA for BMP388 (GP4)
I2C_SCL = 5               # I2C0 SCL for BMP388 (GP5)
LED_PIN = 'LED'           # Built-in LED for status

# Altitude for MSLP pressure correction (450ft in Fairbanks area)
ALTITUDE_FT = 450

# MQTT Topics
TOPIC_WEATHER_TEMP = 'home/weather-station/weather/temperature'
TOPIC_WEATHER_PRESSURE = 'home/weather-station/weather/pressure'
TOPIC_STATUS = 'home/weather-station/status'

# Timing constants
STATUS_INTERVAL_MS = 30000          # Publish status every 30 seconds
DS18B20_CONVERSION_MS = 800         # DS18B20 conversion time + margin


class WeatherStation:
    """Main controller for weather station monitoring.

    Publishes weather data (temperature, pressure) to individual topics
    and a consolidated status message.

    Sensors:
        - DS18B20 outdoor (GP7): Primary weather temperature
        - BMP388 (I2C0 on GP4/GP5): Pressure (temp included in status for reference)

    Attributes:
        runtime: Bootstrap-provided runtime with publish/subscribe/sos APIs.
        device_id (str): Device ID from config.
        led (machine.Pin): Built-in LED pin for heartbeat.
        bmp (bmp3xx.BMP388|None): BMP388 sensor instance if available.
        ds_outdoor (ds18x20.DS18X20|None): DS18B20 bus for outdoor sensor.
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
        self._sos_topic = "home/system/{}/sos".format(self.device_id)

        # Initialize logger
        try:
            self.logger = DeviceLogger(runtime, device_id, min_level='INFO')
            set_global_logger(self.logger)
            self.logger.info("app", "Weather station initializing", {
                "version": "2.1.0",
                "features": ["outdoor_ds18b20", "bmp388_pressure"],
                "pin_config": {
                    "ds18b20_outdoor": DS18B20_OUTDOOR_PIN,
                    "i2c_sda": I2C_SDA,
                    "i2c_scl": I2C_SCL
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

        # BMP388 state (lazy initialization)
        self.bmp = None
        self._bmp_init_attempted = False
        self._bmp_next_retry_ms = 0
        self._bmp_last_sos_ms = 0
        # Schedule BMP388 init 3 seconds after boot
        try:
            self._bmp_next_retry_ms = time.ticks_add(time.ticks_ms(), 3000)
        except Exception:
            self._bmp_next_retry_ms = 0
        self.log_info("sensors", "BMP388 init scheduled", {"delay_ms": 3000})

        # Initialize DS18B20 outdoor sensor
        self.ds_outdoor = None
        self.ds_outdoor_roms = []

        if HAS_ONEWIRE and Pin:
            # Outdoor DS18B20 on GP7
            try:
                self.log_info("sensors", "DS18B20 init starting", {"pin": DS18B20_OUTDOOR_PIN})
                outdoor_pin = Pin(DS18B20_OUTDOOR_PIN)
                ow = onewire.OneWire(outdoor_pin)
                self.ds_outdoor = ds18x20.DS18X20(ow)
                self.log_info("sensors", "DS18B20 scanning bus", {"pin": DS18B20_OUTDOOR_PIN})
                self.ds_outdoor_roms = self.ds_outdoor.scan()
                self.log_info("sensors", "DS18B20 outdoor initialized", {
                    "pin": DS18B20_OUTDOOR_PIN,
                    "devices_found": len(self.ds_outdoor_roms),
                    "roms": [":".join(["{:02x}".format(b) for b in rom]) for rom in self.ds_outdoor_roms]
                })
                if not self.ds_outdoor_roms:
                    self.log_error("sensors", "DS18B20 no devices found on bus", {"pin": DS18B20_OUTDOOR_PIN})
                    self._add_error("ds18b20_outdoor_not_found", "No DS18B20 sensor found on outdoor bus")
                # Flush logs so we see init results immediately
                if self.logger:
                    self.logger.flush()
            except Exception as e:
                self.log_error("sensors", "DS18B20 outdoor initialization failed", {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "pin": DS18B20_OUTDOOR_PIN
                })
                self._add_error("ds18b20_outdoor_init_failed", str(e))
        else:
            self.log_error("sensors", "OneWire not available", {"has_onewire": HAS_ONEWIRE, "has_pin": Pin is not None})

        # State tracking
        self.last_outdoor_temp_f = None       # DS18B20 outdoor (primary weather temp)
        self.last_bmp388_temp_f = None        # BMP388 temp (for status reference only)
        self.last_weather_pressure_inhg = None  # BMP388 pressure

        # Timing state - initialize to current time to prevent immediate publish
        self.last_status_publish = time.ticks_ms()

        # Async temperature reading state for DS18B20 sensor
        self.temp_conversion_started = 0
        self.temp_converting = False
        self.temp_ready = False
        self.pending_outdoor_temp_f = None
        self._ds18b20_error_backoff_until = 0  # Backoff timer for DS18B20 errors

        # Publish initial status after sensors initialize
        try:
            self._bmp_next_retry_ms = time.ticks_add(time.ticks_ms(), 100)
        except Exception:
            pass

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

    # ========== BMP388 Methods ==========

    def _load_stored_calibration(self):
        """Load stored BMP388 calibration from flash."""
        try:
            with open('/lib/bmp_cal.json', 'r') as f:
                data = json.load(f)
                cal = data.get('calibration')
                if cal and len(cal) == 14:
                    self.log_info("sensors", "Loaded stored BMP388 calibration")
                    return tuple(cal)
        except Exception as e:
            self.log_debug("sensors", "No stored calibration found", {"error": str(e)})
        return None

    def _save_calibration(self, cal_tuple):
        """Save BMP388 calibration to flash."""
        try:
            data = {'calibration': list(cal_tuple)}
            with open('/lib/bmp_cal.json', 'w') as f:
                json.dump(data, f)
            self.log_info("sensors", "Saved BMP388 calibration to flash")
            return True
        except Exception as e:
            self.log_error("sensors", "Failed to save calibration", {"error": str(e)})
            return False

    def _reading_is_sane(self, temp_f, pressure_inhg):
        """Check if a BMP388 reading is within reasonable bounds."""
        if temp_f is None or not (-60 <= temp_f <= 120):
            return False
        if pressure_inhg is None or not (25 <= pressure_inhg <= 32):
            return False
        return True

    def _maybe_init_bmp(self):
        """Attempt to initialize BMP388 driver with backoff."""
        if not HAS_BMP3XX:
            return

        try:
            if self.bmp is not None:
                return
            now = time.ticks_ms()

            try:
                if self._bmp_init_attempted and time.ticks_diff(now, self._bmp_next_retry_ms) < 0:
                    return
            except Exception:
                pass

            try:
                self.bmp = bmp3xx.BMP388()
                self.bmp.SetMode(1)  # Continuous mode
                cal_validated = getattr(self.bmp, '_calibration_validated', False)
                self.log_info("sensors", "BMP388 driver initialized", {
                    "mode": "continuous",
                    "calibration_validated": cal_validated
                })

                # Test read and sanity check
                time.sleep_ms(100)
                try:
                    test_temp_c, test_pressure = self.bmp.Reading
                    test_temp_f = test_temp_c * 1.8 + 32
                    altitude_m = ALTITUDE_FT * 0.3048
                    test_pressure_mslp = test_pressure / ((1 - 2.25577e-5 * altitude_m) ** 5.25588)
                    test_pressure_inhg = test_pressure_mslp * 0.02953

                    self.log_info("sensors", "BMP388 test read", {
                        "temp_f": test_temp_f,
                        "pressure_inhg": test_pressure_inhg
                    })

                    if self._reading_is_sane(test_temp_f, test_pressure_inhg):
                        cal_tuple = self.bmp.get_calibration_tuple()
                        self._save_calibration(cal_tuple)
                        self.log_info("sensors", "BMP388 calibration source: fresh sensor read")
                    else:
                        self.log_warning("sensors", "BMP388 reading out of range, trying stored calibration", {
                            "temp_f": test_temp_f,
                            "pressure_inhg": test_pressure_inhg
                        })
                        stored_cal = self._load_stored_calibration()
                        if stored_cal:
                            self.bmp.load_calibration_from_tuple(stored_cal)
                            time.sleep_ms(100)
                            test_temp_c2, test_pressure2 = self.bmp.Reading
                            test_temp_f2 = test_temp_c2 * 1.8 + 32
                            test_pressure_mslp2 = test_pressure2 / ((1 - 2.25577e-5 * altitude_m) ** 5.25588)
                            test_pressure_inhg2 = test_pressure_mslp2 * 0.02953
                            if self._reading_is_sane(test_temp_f2, test_pressure_inhg2):
                                self.log_info("sensors", "BMP388 calibration source: stored backup", {
                                    "temp_f": test_temp_f2,
                                    "pressure_inhg": test_pressure_inhg2
                                })
                            else:
                                self.log_warning("sensors", "BMP388 reading still out of range with stored cal")
                        else:
                            self.log_warning("sensors", "No stored calibration available")

                    self._clear_error("bmp388_init_failed")

                except Exception as test_err:
                    self.log_error("sensors", "BMP388 test read failed", {"error": str(test_err)})
                    self.bmp = None
                    raise test_err

            except Exception as e:
                self.bmp = None
                self._add_error("bmp388_init_failed", str(e))
                self.sos("bmp388_init_failed", str(e))
                self._bmp_next_retry_ms = time.ticks_add(now, 60000)
        finally:
            self._bmp_init_attempted = True

    def _read_bmp388(self):
        """Read temperature and pressure from BMP388."""
        try:
            if not self.bmp:
                self._maybe_init_bmp()
            if not self.bmp:
                return None, None

            temp_c, pressure_hpa = self.bmp.Reading
            temp_f = temp_c * 1.8 + 32

            # Apply MSLP altitude correction
            altitude_m = ALTITUDE_FT * 0.3048
            pressure_mslp = pressure_hpa / ((1 - 2.25577e-5 * altitude_m) ** 5.25588)
            pressure_inhg = pressure_mslp * 0.02953

            return temp_f, pressure_inhg

        except Exception as e:
            self.log_error("sensors", "BMP388 read failed", {"error": str(e)})
            self.bmp = None
            self._bmp_init_attempted = False
            self._bmp_next_retry_ms = time.ticks_add(time.ticks_ms(), 5000)

            # Rate-limit SOS messages
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, self._bmp_last_sos_ms) > 300000:
                self.sos("bmp388_read_error", str(e))
                self._bmp_last_sos_ms = current_time

            return None, None

    # ========== DS18B20 Methods ==========

    def _update_ds18b20_temperatures(self, current_time: int):
        """Update DS18B20 outdoor temperature reading (non-blocking).

        1. Start conversion on outdoor sensor
        2. Wait for conversion to complete
        3. Read temperature
        """
        has_outdoor = self.ds_outdoor and self.ds_outdoor_roms

        if not has_outdoor:
            return

        # Check if we're in error backoff period
        if self._ds18b20_error_backoff_until > 0:
            if time.ticks_diff(current_time, self._ds18b20_error_backoff_until) < 0:
                return  # Still in backoff period
            self._ds18b20_error_backoff_until = 0  # Backoff expired, try again

        # Start conversion if not in progress
        if not self.temp_converting and not self.temp_ready:
            try:
                self.ds_outdoor.convert_temp()
                self.temp_conversion_started = current_time
                self.temp_converting = True
                self._clear_error("ds18b20_read_error")
            except Exception as e:
                self.log_error("sensors", "Failed to start temp conversion", {
                    "error": str(e) if str(e) else "(empty)",
                    "error_type": type(e).__name__,
                    "error_args": str(e.args) if hasattr(e, 'args') else "N/A",
                    "pin": DS18B20_OUTDOOR_PIN,
                    "roms_count": len(self.ds_outdoor_roms) if self.ds_outdoor_roms else 0
                })
                self._add_error("ds18b20_read_error", str(e) or type(e).__name__)
                # Backoff for 30 seconds before retrying
                self._ds18b20_error_backoff_until = time.ticks_add(current_time, 30000)
                return

        # Check if conversion is complete
        if self.temp_converting:
            if time.ticks_diff(current_time, self.temp_conversion_started) >= DS18B20_CONVERSION_MS:
                self.temp_converting = False

                # Read outdoor temperature
                try:
                    temp_c = self.ds_outdoor.read_temp(self.ds_outdoor_roms[0])
                    temp_f = temp_c * 1.8 + 32
                    self.pending_outdoor_temp_f = temp_f
                    self.last_outdoor_temp_f = temp_f
                    self._clear_error("ds18b20_outdoor_read_error")
                except Exception as e:
                    self.log_error("sensors", "Failed to read outdoor temperature", {"error": str(e)})
                    self._add_error("ds18b20_outdoor_read_error", str(e))
                    self.pending_outdoor_temp_f = None
                    # Backoff for 30 seconds before retrying
                    self._ds18b20_error_backoff_until = time.ticks_add(current_time, 30000)

                self.temp_ready = True

    # ========== Status Publishing ==========

    def _get_uptime_seconds(self, current_time: int) -> int:
        """Get device uptime in seconds."""
        return time.ticks_diff(current_time, self._boot_time) // 1000

    def _build_status_message(self, current_time: int) -> dict:
        """Build consolidated status message.

        Weather temperature comes from DS18B20 outdoor sensor.
        BMP388 temperature is included for reference/comparison.
        """
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
            "weather": {
                "temperature_f": self.last_outdoor_temp_f,  # DS18B20 outdoor (primary)
                "bmp388_temperature_f": self.last_bmp388_temp_f,  # BMP388 (for reference)
                "pressure_inhg": self.last_weather_pressure_inhg
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
        """Publish all sensor data and consolidated status.

        Weather temperature: DS18B20 outdoor (primary)
        Weather pressure: BMP388
        BMP388 temperature: Stored for status reference only
        """
        current_time = time.ticks_ms()

        # Read BMP388 for pressure and reference temperature
        bmp388_temp_f, pressure_inhg = self._read_bmp388()
        if bmp388_temp_f is not None and pressure_inhg is not None:
            # Publish pressure from BMP388
            self.runtime.publish(TOPIC_WEATHER_PRESSURE, "{:.2f}".format(pressure_inhg))
            self.last_bmp388_temp_f = bmp388_temp_f
            self.last_weather_pressure_inhg = pressure_inhg
            self._clear_error("bmp388_no_reading")
        else:
            self._add_error("bmp388_no_reading", "No BMP388 reading")

        # Publish outdoor temperature from DS18B20 (primary weather temp)
        if self.pending_outdoor_temp_f is not None:
            self.runtime.publish(TOPIC_WEATHER_TEMP, "{:.1f}".format(self.pending_outdoor_temp_f))
            self.last_outdoor_temp_f = self.pending_outdoor_temp_f
            self._clear_error("outdoor_temp_no_reading")
        else:
            self._add_error("outdoor_temp_no_reading", "No outdoor temperature reading")

        # Publish consolidated status
        status = self._build_status_message(current_time)
        try:
            payload = json.dumps(status)
            self.runtime.publish(TOPIC_STATUS, payload)
            self.log_debug("mqtt", "Published status", {"size": len(payload)})
        except Exception as e:
            self.log_error("mqtt", "Failed to publish status", {"error": str(e)})

        # Reset temperature ready flag
        self.temp_ready = False
        self.pending_outdoor_temp_f = self.last_outdoor_temp_f

        # Toggle LED
        if self.led:
            try:
                self.led.value(0 if self.led.value() else 1)
            except Exception:
                pass

        # Periodic GC
        try:
            gc.collect()
        except Exception:
            pass

    def update(self):
        """Main update loop - called frequently from tick()."""
        current_time = time.ticks_ms()

        # Try initializing BMP if scheduled
        try:
            self._maybe_init_bmp()
        except Exception:
            pass

        # Update both DS18B20 temperatures (non-blocking)
        self._update_ds18b20_temperatures(current_time)

        # Publish status every 30 seconds
        if time.ticks_diff(current_time, self.last_status_publish) >= STATUS_INTERVAL_MS:
            if not self.temp_converting or self.temp_ready:
                self._publish_status()
                self.last_status_publish = current_time

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


# Module-level state
_station = None
_runtime = None


def init(runtime):
    """Initialize the app with the bootstrap-provided runtime."""
    global _station, _runtime
    _runtime = runtime

    cfg = load_device_config()
    device_id = cfg.get("device_id") or "weather-station"

    try:
        print("[APP] Initializing weather-station as {}".format(device_id))
    except Exception:
        pass

    _station = WeatherStation(runtime, device_id)

    try:
        print("[APP] Weather station ready")
    except Exception:
        pass


def tick():
    """Periodic work slice. Must return quickly."""
    global _station
    if _station:
        _station.update()


def shutdown(reason=""):
    """Cleanup before OTA or reset."""
    global _station
    if _station and _station.logger:
        _station.log_info("app", "Shutting down", {"reason": reason})
        _station.logger.flush()
