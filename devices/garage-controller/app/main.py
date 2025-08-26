"""
Garage Controller Pico W Application

Controls and monitors:
- Garage door (relay + reed switches)
- Flood light (relay)
- Environmental sensors (BMP388 for temp/pressure, DS18B20 for freezer temp)

Entry point: main()
"""

try:
    import time
except Exception:
    import sys as time  # type: ignore
try:
    import machine
except Exception:
    import sys as machine  # type: ignore
import onewire
import ds18x20
from machine import Pin, I2C
import bmp3xx  # Provided in shared/vendor and deployed to /lib
from shared.config_manager import load_device_config
try:
    import ujson as json  # type: ignore
except Exception:
    import json  # type: ignore

# Pin Definitions
GARAGE_DOOR_RELAY = 2
FLOOD_LIGHT_RELAY = 5
DOOR_OPEN_SW = 3
DOOR_CLOSED_SW = 4
DS18B20_PIN = 8
I2C_SDA = 6
I2C_SCL = 7
LED_PIN = 'LED'  # Built-in LED

# MQTT Topics (from design_doc.md)
TOPIC_DOOR_STATUS = 'home/garage/door/status'
TOPIC_DOOR_COMMAND = 'home/garage/door/command'
TOPIC_LIGHT_STATUS = 'home/garage/light/status'
TOPIC_LIGHT_COMMAND = 'home/garage/light/command'
TOPIC_WEATHER_TEMP = 'home/garage/weather/temperature'
TOPIC_WEATHER_PRESSURE = 'home/garage/weather/pressure'
TOPIC_FREEZER_TEMP = 'home/garage/freezer/temperature'

class GarageController:
    """Main controller for garage door and related components.

    Attributes:
        mqtt (shared.mqtt_client.Mqtt): MQTT client wrapper.
        led (machine.Pin): Built-in LED pin for heartbeat.
        door_relay (machine.Pin): Output to garage door relay.
        light_relay (machine.Pin): Output to flood light relay.
        door_open_sw (machine.Pin): Input from "door open" reed switch (active-low).
        door_closed_sw (machine.Pin): Input from "door closed" reed switch (active-low).
        bmp (bmp3xx.BMP3XX|None): BMP388 sensor instance if available.
        ds_sensor (ds18x20.DS18X20|None): DS18B20 bus instance if available.
        ds_roms (list): Discovered DS18B20 ROMs.
        last_door_state (str): Last published door state.
        last_light_state (bool): Last known flood light state.
        last_update (int): ms timestamp for periodic sensor update.
    """
    
    def __init__(self, mqtt_client, device_id: str):
        """Initialize hardware and MQTT client.

        Args:
            mqtt_client (shared.mqtt_client.Mqtt): Connected MQTT client wrapper.
        """
        self.mqtt = mqtt_client
        self.device_id = device_id
        self._sos_topic = "home/system/{}/sos".format(self.device_id)
        self.led = Pin(LED_PIN, Pin.OUT)
        
        # Initialize relays
        self.door_relay = Pin(GARAGE_DOOR_RELAY, Pin.OUT, value=0)  # Active high
        self.light_relay = Pin(FLOOD_LIGHT_RELAY, Pin.OUT, value=0)  # Active high
        
        # Initialize door sensors with pull-ups
        self.door_open_sw = Pin(DOOR_OPEN_SW, Pin.IN, Pin.PULL_UP)
        self.door_closed_sw = Pin(DOOR_CLOSED_SW, Pin.IN, Pin.PULL_UP)
        
        # Initialize BMP388 driver (uses I2C bus 1 with GP6/GP7 by default per PINOUT)
        # Reason: Our vendor driver internally initializes I2C for Pico W.
        # Guards:
        #  - If SDA/SCL are held low (miswire), I2C ops may hang. Check lines first.
        #  - Only attempt init if an address 0x76/0x77 is detected on bus scan.
        # Defer actual BMP driver instantiation to runtime to avoid boot-looping on sensor faults.
        # We'll perform a quick diagnostic scan here, but not construct the driver yet.
        self.bmp = None
        self._bmp_init_attempted = False
        self._bmp_next_retry_ms = 0  # next allowed attempt time in ticks_ms
        try:
            sda_ok = False
            scl_ok = False
            try:
                sda_ok = bool(Pin(I2C_SDA, Pin.IN, Pin.PULL_UP).value())
                scl_ok = bool(Pin(I2C_SCL, Pin.IN, Pin.PULL_UP).value())
            except Exception:
                pass

            # Perform a quick scan for diagnostic logging (even if lines look low)
            addrs = []
            try:
                _di = I2C(1, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400000)
                time.sleep_ms(10)
                addrs = _di.scan()
            except Exception:
                addrs = []
            try:
                print("[DIAG][I2C] SDA={} SCL={} scan={}".format(int(sda_ok), int(scl_ok), [hex(a) for a in addrs]))
            except Exception:
                pass
            # Schedule a first init attempt shortly after boot to let system settle
            try:
                self._bmp_next_retry_ms = time.ticks_add(time.ticks_ms(), 3000)
            except Exception:
                self._bmp_next_retry_ms = 0
        except Exception:
            # Ignore diagnostics errors
            pass
        
        # Initialize DS18B20
        self.ds_pin = Pin(DS18B20_PIN)
        try:
            self.ds_sensor = ds18x20.DS18X20(onewire.OneWire(self.ds_pin))
            self.ds_roms = self.ds_sensor.scan()
        except Exception as e:
            self.ds_sensor = None
            self.ds_roms = []
            try:
                self.sos("ds18b20_init_failed", "{}".format(e))
            except Exception:
                pass
        
        # State tracking
        self._expected = None  # type: ignore  # "open"|"closed"|None, to better infer opening/closing
        # Initialize to a safe placeholder before first read to avoid attribute access during inference
        self.last_door_state = 'unknown'
        self.last_light_state = False
        self.last_update = 0
        # Now compute the true initial state
        self.last_door_state = self.get_door_state()
        
        # Setup MQTT callbacks
        # Reason: shared.mqtt_client.Mqtt exposes set_message_handler()
        try:
            self.mqtt.set_message_handler(self.mqtt_callback)
        except Exception:
            pass
        try:
            self.mqtt.subscribe(TOPIC_DOOR_COMMAND)
            self.mqtt.subscribe(TOPIC_LIGHT_COMMAND)
        except Exception:
            pass
        # Publish initial states so subscribers have baseline
        try:
            self.mqtt.publish(TOPIC_DOOR_STATUS, self.last_door_state)
            self.mqtt.publish(TOPIC_LIGHT_STATUS, 'on' if self.last_light_state else 'off')
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
        # Infer direction from last known or expected target
        expected = getattr(self, "_expected", None)
        last = getattr(self, "last_door_state", None)
        if expected == 'open' or last == 'closed':
            return 'opening'
        if expected == 'closed' or last == 'open':
            return 'closing'
        # Fallback if unknown
        if last in ('opening', 'open'):
            return 'opening'
        if last in ('closing', 'closed'):
            return 'closing'
        return 'closing'
    
    def toggle_garage_door(self):
        """Momentarily activate the door relay to simulate a wall-button press.

        Returns:
            None: Relay is pulsed for 500ms.
        """
        self.door_relay.value(1)
        time.sleep(0.5)  # Pulse relay for 500ms
        self.door_relay.value(0)
    
    def set_light(self, state):
        """Set flood light state and publish status.

        Args:
            state (bool): True to turn on, False to turn off.
        """
        self.light_relay.value(1 if state else 0)
        self.last_light_state = state
        self.mqtt.publish(TOPIC_LIGHT_STATUS, 'on' if state else 'off')
    
    def read_bmp388(self):
        """Read temperature and pressure from BMP388.

        Returns:
            tuple[float|None, float|None]: (temp_f, pressure_inhg) or (None, None) on error.
        """
        try:
            if not self.bmp:
                # Attempt lazy init if due
                try:
                    self._maybe_init_bmp()
                except Exception:
                    pass
            if not self.bmp:
                return None, None
            # Vendor driver exposes Reading -> (temp_C, pressure_units)
            temp_c, pressure = self.bmp.Reading
            # Convert to Fahrenheit; pressure conversion depends on driver units.
            # Reason: Driver returns scaled value; publish both raw and inHg best-effort.
            pressure_inhg = pressure * 0.02953  # If pressure is in hPa, this yields inHg.
            return temp_c * 1.8 + 32, pressure_inhg
        except Exception as e:
            try:
                print(f"BMP388 read error: {e}")
            except Exception:
                pass
            try:
                self.sos("bmp388_read_error", f"{e}")
            except Exception:
                pass
            return None, None
    
    def read_ds18b20(self):
        """Read temperature from DS18B20.

        Returns:
            float|None: Temperature in Fahrenheit, or None on error.
        """
        try:
            if not self.ds_sensor:
                return None
            self.ds_sensor.convert_temp()
            time.sleep_ms(750)  # Wait for conversion
            if self.ds_roms:
                temp_c = self.ds_sensor.read_temp(self.ds_roms[0])
                return temp_c * 1.8 + 32  # Convert to °F
        except Exception as e:
            try:
                print(f"DS18B20 read error: {e}")
            except Exception:
                pass
            try:
                self.sos("ds18b20_read_error", f"{e}")
            except Exception:
                pass
        return None

    def sos(self, error: str, message: str = "") -> None:
        """Publish an SOS diagnostic event without raising.

        Args:
            error (str): Error code, e.g., 'bmp388_init_failed'.
            message (str): Optional human-readable details.

        Returns:
            None
        """
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
            self.mqtt.publish(self._sos_topic, body)
        except Exception:
            # Never raise from SOS
            pass
    
    def mqtt_callback(self, topic, msg):
        """Handle incoming MQTT messages.

        Args:
            topic (str): Topic string (already decoded by `shared.mqtt_client`).
            msg (bytes|str): Payload; may be bytes from umqtt.
        """
        # Ensure payload is str for comparisons
        try:
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8')
        except Exception:
            pass
        
        # Debug: log inbound commands
        try:
            print("[APP][MQTT] rx:", topic, msg)
        except Exception:
            pass

        if topic == TOPIC_DOOR_COMMAND and msg in ['open', 'close', 'toggle']:
            # Always pulse the relay for open/close/toggle to match wall-button behavior
            # while still recording intent to help state inference.
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
        """Read all sensors and publish updates.

        Publishes:
            - `home/garage/door/status`: on any door state change.
            - `home/garage/weather/*`: temperature (F) and pressure (inHg) every 30s.
            - `home/garage/freezer/temperature`: (F) every 30s.
        """
        current_time = time.ticks_ms()
        # Try initializing BMP driver if scheduled
        try:
            self._maybe_init_bmp()
        except Exception:
            pass
        
        # Update door state if changed
        door_state = self.get_door_state()
        if door_state != self.last_door_state:
            self.mqtt.publish(TOPIC_DOOR_STATUS, door_state)
            self.last_door_state = door_state
            # Clear expected target once we hit terminal state
            if door_state in ('open', 'closed'):
                self._expected = None

        # Update sensors every 30 seconds
        if time.ticks_diff(current_time, self.last_update) > 30000:
            # Read and publish weather data
            temp_f, pressure_inhg = self.read_bmp388()
            if temp_f is not None and pressure_inhg is not None:
                self.mqtt.publish(TOPIC_WEATHER_TEMP, f"{temp_f:.1f}")
                self.mqtt.publish(TOPIC_WEATHER_PRESSURE, f"{pressure_inhg:.2f}")
            
            # Read and publish freezer temperature
            temp_f = self.read_ds18b20()
            if temp_f is not None:
                self.mqtt.publish(TOPIC_FREEZER_TEMP, f"{temp_f:.1f}")
            
            self.last_update = current_time
            # Blink LED to show activity (portable across ports)
            try:
                self.led.value(0 if self.led.value() else 1)
            except Exception:
                pass

    def _maybe_init_bmp(self):
        """Attempt to initialize BMP388 driver with backoff and diagnostics.

        This method is safe to call frequently; it only attempts init when due
        and when basic I2C line checks and device presence look sane.

        Returns:
            None
        """
        try:
            if self.bmp is not None:
                return
            now = time.ticks_ms()
            # Respect backoff schedule
            try:
                if self._bmp_init_attempted and time.ticks_diff(now, self._bmp_next_retry_ms) < 0:
                    return
            except Exception:
                # If ticks functions not available, proceed cautiously once
                pass

            # Basic line state check
            try:
                sda_ok = bool(Pin(I2C_SDA, Pin.IN, Pin.PULL_UP).value())
                scl_ok = bool(Pin(I2C_SCL, Pin.IN, Pin.PULL_UP).value())
            except Exception:
                sda_ok = True
                scl_ok = True

            # Scan for device
            addrs = []
            try:
                _di = I2C(1, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400000)
                time.sleep_ms(5)
                addrs = _di.scan()
            except Exception:
                addrs = []

            if not (sda_ok and scl_ok):
                try:
                    print("[BMP][INIT] I2C lines not idle; deferring init. SDA={} SCL={}".format(int(sda_ok), int(scl_ok)))
                except Exception:
                    pass
                self._schedule_bmp_retry(now, 15000)
                return

            if not (0x76 in addrs or 0x77 in addrs):
                try:
                    print("[BMP][INIT] No BMP3xx address on bus; deferring. scan=", [hex(a) for a in addrs])
                except Exception:
                    pass
                self._schedule_bmp_retry(now, 30000)
                return

            # Optional: quick probe of chip-id register (0x00)
            try:
                addr = 0x76 if 0x76 in addrs else 0x77
                _di.writeto(addr, b"\x00")
                _id = _di.readfrom(addr, 1)[0]
                try:
                    print("[BMP][INIT] probe id=", "0x{:02x}".format(_id))
                except Exception:
                    pass
            except Exception:
                pass

            # Try construct driver
            try:
                self.bmp = bmp3xx.BMP388()
                try:
                    print("[BMP][INIT] driver ready")
                except Exception:
                    pass
                return
            except Exception as e1:
                try:
                    self.bmp = bmp3xx.BMP3XX()
                    print("[BMP][INIT] fallback driver ready")
                    return
                except Exception as e2:
                    self.bmp = None
                    try:
                        self.sos("bmp388_init_failed", "{} / {}".format(e1, e2))
                    except Exception:
                        pass
                    self._schedule_bmp_retry(now, 60000)
        finally:
            self._bmp_init_attempted = True

    def _schedule_bmp_retry(self, now_ms, delay_ms):
        """Schedule the next BMP init attempt.

        Args:
            now_ms (int): Current ticks_ms time.
            delay_ms (int): Delay before next attempt.

        Returns:
            None
        """
        try:
            self._bmp_next_retry_ms = time.ticks_add(now_ms, delay_ms)
        except Exception:
            # If ticks_add not available, fall back to immediate retry later
            self._bmp_next_retry_ms = 0

def main():
    """Main application loop.

    Loads MQTT configuration, connects, initializes `GarageController`, and
    runs the main polling loop. Publishes a simple health heartbeat.

    Returns:
        None
    """
    # Load MQTT config
    cfg = load_device_config()
    device_id = cfg.get("device_id") or "device-unknown"
    host = cfg.get("mqtt_host") or ""
    port = cfg.get("mqtt_port") or 1883
    user = cfg.get("mqtt_user") or None
    password = cfg.get("mqtt_password") or None

    # Initialize MQTT client (shared wrapper)
    from shared.mqtt_client import Mqtt
    mqtt = Mqtt(host, port, user, password, client_id="{}-app".format(device_id))
    # Try to connect; if not available, continue gracefully (bootstrap will keep system MQTT alive)
    try:
        if mqtt.connect():
            try:
                print("[APP][MQTT] connected")
            except Exception:
                pass
    except Exception:
        pass

    # Initialize controller
    try:
        try:
            print("[APP] init controller...")
        except Exception:
            pass
        controller = GarageController(mqtt, device_id)
        try:
            print("[APP] controller ready")
        except Exception:
            pass
    except Exception as e:
        # Surface the failure clearly and let bootstrap catch the exception
        try:
            print("[APP] controller init failed:", e)
        except Exception:
            pass
        try:
            # Minimal SOS without assuming mqtt wrapper shape
            base = "home/system/{}/sos".format(device_id)
            body = json.dumps({
                "device_id": device_id,
                "error": "controller_init_failed",
                "message": str(e),
                "timestamp": time.ticks_ms(),
            })
            mqtt.publish(base, body)
        except Exception:
            pass
        raise

    print("Garage controller started")

    # App-level system health heartbeat (non-retained).
    # Reason: While app runs, bootstrap loop is blocked; keep-alive here helps observability.
    system_health_topic = "home/system/{}/health".format(device_id)
    last_health = 0

    # Main loop
    while True:
        try:
            mqtt.check_msg()  # Check for incoming MQTT messages
        except Exception:
            pass
        controller.update_sensors()
        # Periodic health heartbeat (~30s)
        try:
            now = time.ticks_ms()
            if now and (now - last_health) >= 30000:
                last_health = now
                mqtt.publish(system_health_topic, "online")
        except Exception:
            pass
        time.sleep(0.1)  # Small delay to prevent tight loop
