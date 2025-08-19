"""
Garage Controller Pico W Application

Controls and monitors:
- Garage door (relay + reed switches)
- Flood light (relay)
- Environmental sensors (BMP388 for temp/pressure, DS18B20 for freezer temp)

Entry point: main()
"""

import time
import machine
import onewire
import ds18x20
from machine import Pin, I2C
import bmp3xx  # Provided in shared/vendor and deployed to /lib
from shared.config_manager import load_device_config

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
    """Main controller for garage door and related components."""
    
    def __init__(self, mqtt_client):
        """Initialize hardware and MQTT client."""
        self.mqtt = mqtt_client
        self.led = Pin(LED_PIN, Pin.OUT)
        
        # Initialize relays
        self.door_relay = Pin(GARAGE_DOOR_RELAY, Pin.OUT, value=0)  # Active high
        self.light_relay = Pin(FLOOD_LIGHT_RELAY, Pin.OUT, value=0)  # Active high
        
        # Initialize door sensors with pull-ups
        self.door_open_sw = Pin(DOOR_OPEN_SW, Pin.IN, Pin.PULL_UP)
        self.door_closed_sw = Pin(DOOR_CLOSED_SW, Pin.IN, Pin.PULL_UP)
        
        # Initialize BMP388 driver (uses I2C bus 1 with GP6/GP7 by default per PINOUT)
        # Reason: Our vendor driver internally initializes I2C for Pico W.
        self.bmp = None
        try:
            try:
                self.bmp = bmp3xx.BMP388()
            except Exception:
                # Fallback to base class if specific not available
                self.bmp = bmp3xx.BMP3XX()
        except Exception as e:
            # Sensor not present or I2C error; continue without BMP388
            self.bmp = None
        
        # Initialize DS18B20
        self.ds_pin = Pin(DS18B20_PIN)
        try:
            self.ds_sensor = ds18x20.DS18X20(onewire.OneWire(self.ds_pin))
            self.ds_roms = self.ds_sensor.scan()
        except Exception:
            self.ds_sensor = None
            self.ds_roms = []
        
        # State tracking
        self.last_door_state = self.get_door_state()
        self.last_light_state = False
        self.last_update = 0
        
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
    
    def get_door_state(self):
        """Read door state from sensors."""
        open_sw = not self.door_open_sw.value()  # Active low
        closed_sw = not self.door_closed_sw.value()  # Active low
        
        if open_sw and not closed_sw:
            return 'open'
        elif not open_sw and closed_sw:
            return 'closed'
        elif not open_sw and not closed_sw:
            return 'in_between'  # Transitioning
        else:
            return 'error'  # Invalid state (both switches active)
    
    def toggle_garage_door(self):
        """Toggle garage door state."""
        self.door_relay.value(1)
        time.sleep(0.5)  # Pulse relay for 500ms
        self.door_relay.value(0)
    
    def set_light(self, state):
        """Set flood light state."""
        self.light_relay.value(1 if state else 0)
        self.last_light_state = state
        self.mqtt.publish(TOPIC_LIGHT_STATUS, 'on' if state else 'off')
    
    def read_bmp388(self):
        """Read temperature and pressure from BMP388."""
        try:
            if not self.bmp:
                return None, None
            # Vendor driver exposes Reading -> (temp_C, pressure_units)
            temp_c, pressure = self.bmp.Reading
            # Convert to Fahrenheit; pressure conversion depends on driver units.
            # Reason: Driver returns scaled value; publish both raw and inHg best-effort.
            pressure_inhg = pressure * 0.02953  # If pressure is in hPa, this yields inHg.
            return temp_c * 1.8 + 32, pressure_inhg
        except Exception as e:
            print(f"BMP388 read error: {e}")
            return None, None
    
    def read_ds18b20(self):
        """Read temperature from DS18B20."""
        try:
            if not self.ds_sensor:
                return None
            self.ds_sensor.convert_temp()
            time.sleep_ms(750)  # Wait for conversion
            if self.ds_roms:
                temp_c = self.ds_sensor.read_temp(self.ds_roms[0])
                return temp_c * 1.8 + 32  # Convert to °F
        except Exception as e:
            print(f"DS18B20 read error: {e}")
        return None
    
    def mqtt_callback(self, topic, msg):
        """Handle incoming MQTT messages.

        Args:
            topic (str): Topic string (already decoded by shared.mqtt_client).
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
            self.toggle_garage_door()
        elif topic == TOPIC_LIGHT_COMMAND:
            if msg == 'on':
                self.set_light(True)
            elif msg == 'off':
                self.set_light(False)
            elif msg == 'toggle':
                self.set_light(not self.last_light_state)
    
    def update_sensors(self):
        """Read all sensors and publish updates."""
        current_time = time.ticks_ms()
        
        # Update door state if changed
        door_state = self.get_door_state()
        if door_state != self.last_door_state:
            self.mqtt.publish(TOPIC_DOOR_STATUS, door_state)
            self.last_door_state = door_state
        
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

def main():
    """Main application loop."""
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
    controller = GarageController(mqtt)

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
