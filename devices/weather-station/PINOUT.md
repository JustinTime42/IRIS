# Weather Station Pinout

## Overview

The weather-station Pico W is mounted **inside the weather enclosure** to monitor outdoor weather conditions using:
- **DS18B20 (GP7)**: Outdoor temperature (primary weather temp)
- **BMP388 (I2C0 on GP4/GP5)**: Barometric pressure (temp included in status for reference)

All sensors use direct short-wire connections within the enclosure - no long cable runs required.

## Power

- **USB Power**: Powers the Pico W (cable exits weather enclosure)
- **3V3 (Pin 36)**: 3.3V output for sensors
- **GND**: Ground connections

## GPIO Pin Assignments

| GPIO | Mode   | Function       | Description            | Notes                                  |
| ---- | ------ | -------------- | ---------------------- | -------------------------------------- |
| GP4  | I2C    | SDA            | BMP388 data line       | I2C0 bus                               |
| GP5  | I2C    | SCL            | BMP388 clock line      | I2C0 bus, 50kHz for reliability        |
| GP7  | 1-Wire | DS18B20 Data   | Outdoor temperature    | Requires 4.7kΩ external pull-up to 3V3 |
| GP25 | Output | Built-in LED   | Status/heartbeat       | Toggles every 30s                      |

## External Components

### BMP388 Temperature/Pressure Sensor

**Sensor Specifications:**
- Temperature range: -40°C to +85°C
- Pressure range: 300-1250 hPa
- I2C address: 0x77 (SDO floating/unconnected)

**Connections:**
| Sensor Pin | Connect To | Notes |
|------------|------------|-------|
| VIN/VCC | 3V3 | Power (3.3V) |
| GND | GND | Ground |
| SDA/SDI | GP4 | I2C data (pin 6) |
| SCL/SCK | GP5 | I2C clock (pin 7) |
| CS | 3V3 | Tie HIGH for I2C mode |
| SDO | (leave unconnected) | Floats to address 0x77 |

**I2C Mode Configuration:**
- **CS pin must be tied to VCC (3V3)** to enable I2C mode
- **SDO pin can be left unconnected** - floats to address 0x77
- If your breakout board has no CS/SDO pins exposed, they are likely already configured for I2C

**I2C Configuration:**
- Bus: I2C0 (hardware I2C on GP4/GP5)
- Frequency: 50kHz (reduced for reliability)
- Mode: Continuous sampling

**Placement:**
- Mount in ventilated weather enclosure (Stevenson screen style)
- Keep away from direct sunlight
- Ensure good airflow around sensor
- Position at typical "weather station height" (1.2-1.5m above ground)

**Calibration Notes:**
- Factory calibration stored in sensor NVM
- Device reads calibration 3x at startup and validates consistency
- Good calibration is saved to `/lib/bmp_cal.json` for cold-boot fallback
- Altitude correction applied: 450ft (configurable in code)

### DS18B20 Temperature Sensor (Outdoor - GP7)

Primary outdoor temperature sensor, more accurate than BMP388 for temperature readings.

**Connections:**
| Sensor Wire | Connect To | Notes |
|-------------|------------|-------|
| Red (VCC) | 3V3 | Power |
| Black (GND) | GND | Ground |
| Yellow/White (DATA) | GP7 | 1-Wire data |
| - | 4.7kΩ between GP7 and 3V3 | Pull-up resistor |

**Placement:**
- Mount in weather enclosure alongside BMP388
- Keep away from direct sunlight
- Ensure good airflow around sensor
- Waterproof probe recommended for outdoor use

**Wire Run Notes:**
- Short run within weather enclosure (a few inches)
- 4.7kΩ pull-up resistor required
- Keep wiring neat to avoid interference with airflow

## Wiring Overview

```
┌─────────────────────────────────────────────────────┐
│              WEATHER ENCLOSURE                       │
│                                                      │
│    ┌──────────────────────────────────────────┐     │
│    │         Pico W (weather-station)          │     │
│    │                                           │     │
│    │  GP4 ← BMP388 SDA                        │     │
│    │  GP5 ← BMP388 SCL                        │     │
│    │  GP7 ← DS18B20 outdoor (direct wire)     │     │
│    │                                           │     │
│    └─────────────────┬─────────────────────────┘     │
│                      │ USB cable exits enclosure     │
│    ┌─────────────────┴─────────────────────┐        │
│    │  Short direct wiring (inches):        │        │
│    │  • BMP388 breakout board              │        │
│    │  • DS18B20 waterproof probe           │        │
│    │  • 4.7kΩ pull-up resistor             │        │
│    └───────────────────────────────────────┘        │
│                                                      │
└─────────────────────────────────────────────────────┘
        │
        │ USB power cable only
        ▼
    To power source
```

**Note:** All sensor wiring is contained within the weather enclosure. The only cable exiting is the USB power cable.

---

## Installation Notes

### 1. Pico W Placement

**Location:**
- Mounted directly inside the weather enclosure
- Protected from rain/moisture by enclosure design
- USB cable routed out through bottom or grommet

**Benefits of Internal Mounting:**
- Extremely short I2C run to BMP388 (inches)
- Extremely short 1-Wire run to DS18B20 (inches)
- No long-cable signal integrity issues
- Simplified wiring and installation
- WiFi handles the distance to the network

### 2. Weather Enclosure

**Requirements:**
- Ventilated housing that allows airflow
- Protection from rain and direct sunlight
- White or reflective exterior to minimize solar heating
- "Stevenson screen" style louvered enclosure recommended
- Must accommodate Pico W + sensors + wiring

**Self-Heating Mitigation:**
- BMP388 generates minimal self-heat
- Pico W generates some heat - position away from sensors if possible
- Ventilated enclosure allows ambient air circulation
- Consider positioning Pico W at bottom of enclosure (heat rises)

### 3. Signal Integrity

**I2C (BMP388):**
- Very short cable run (inches) - no signal integrity concerns
- 50kHz clock rate configured for maximum reliability

**1-Wire (DS18B20):**
- 4.7kΩ pull-up resistor required
- Short run means pull-up value is not critical
- Keep wiring away from power cables

## Verification Checklist

### Pre-Installation (Bench Test)

- [ ] BMP388 detected on I2C bus (address 0x76 or 0x77)
- [ ] BMP388 CS pin tied to 3V3 (if exposed)
- [ ] BMP388 SDO pin tied appropriately for desired address (if exposed)
- [ ] BMP388 pressure reads reasonable value (~29-30 inHg at ~500ft elevation)
- [ ] DS18B20 outdoor (GP7) detected on 1-Wire bus
- [ ] DS18B20 outdoor temperature reads correctly at room temperature
- [ ] 4.7kΩ pull-up resistor installed on GP7
- [ ] WiFi connects successfully
- [ ] MQTT publishes to correct topics

### Post-Installation

- [ ] DS18B20 outdoor tracks outdoor conditions accurately
- [ ] BMP388 pressure matches nearby weather stations (±0.1 inHg)
- [ ] Calibration saved to flash (`/lib/bmp_cal.json` exists)
- [ ] All MQTT topics publishing correctly
- [ ] Status publishing every 30 seconds
- [ ] Status includes both DS18B20 temp and BMP388 temp for comparison
- [ ] No condensation in weather enclosure (check after 24 hours)
- [ ] USB cable exit point is sealed/weatherproof

## MQTT Topics Reference

### Individual Sensor Topics

| Topic | Source | Description | Format |
|-------|--------|-------------|--------|
| `home/weather-station/weather/temperature` | DS18B20 (GP7) | Outdoor temperature (primary) | Float string, °F (e.g., "-20.5") |
| `home/weather-station/weather/pressure` | BMP388 | Barometric pressure | Float string, inHg (e.g., "29.87") |

### Consolidated Status (Published Every 30 Seconds)

**Topic:** `home/weather-station/status`

**Payload:**
```json
{
  "timestamp": 1703789400000,
  "uptime_s": 3600,
  "health": "online",
  "weather": {
    "temperature_f": -20.5,
    "bmp388_temperature_f": -18.2,
    "pressure_inhg": 29.87
  },
  "errors": [],
  "memory": {
    "free": 150000,
    "allocated": 50000
  }
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | int | Device time in ticks_ms |
| `uptime_s` | int | Seconds since boot |
| `health` | string | `"online"` or `"degraded"` (if errors present) |
| `weather.temperature_f` | float/null | Outdoor temperature from DS18B20 (primary) |
| `weather.bmp388_temperature_f` | float/null | BMP388 temperature (for reference/comparison) |
| `weather.pressure_inhg` | float/null | Barometric pressure in inHg (MSLP corrected) |
| `errors` | array | Active errors with code, message, since timestamp |
| `memory.free` | int | Free memory in bytes |
| `memory.allocated` | int | Allocated memory in bytes |

### Bootstrap-Managed Topics

| Topic | Description |
|-------|-------------|
| `home/system/weather-station/health` | LWT: `"offline"` when device disconnects |
| `home/system/weather-station/sos` | Critical bootstrap errors |
| `home/system/weather-station/update` | OTA update trigger (subscribe) |

## Troubleshooting

### BMP388 Not Found

1. Check wiring: SDA→GP4, SCL→GP5, VCC→3V3, GND→GND
2. Verify CS pin is tied to 3V3 (if exposed on breakout)
3. Run I2C scan to verify device at 0x77: `I2C(0, scl=Pin(5), sda=Pin(4)).scan()`
4. Check for cold solder joints
5. If device shows at different address, update ADDR in bmp3xx.py

### BMP388 Reading Errors

1. Out-of-range readings: May indicate calibration corruption
   - Device will attempt to load stored calibration from `/lib/bmp_cal.json`
   - If no stored calibration, readings may be inaccurate until warmer conditions
2. CRC/communication errors: Check wiring connections
3. Pressure way off: Verify altitude setting in code (ALTITUDE_FT = 450)

### DS18B20 Not Found

1. Check wiring: Data→GP7, VCC→3V3, GND→GND
2. Verify 4.7kΩ pull-up between GP7 and 3V3
3. Check device logs for "DS18B20 outdoor initialized" message
4. Check for cold solder joints

### Temperature Reading Errors

1. CRC errors: Check wiring, add shielding if near interference
2. Always reads 85°C/185°F: Conversion not complete (timing issue)
3. Wildly wrong values: Pull-up resistor missing or wrong value
4. Compare DS18B20 outdoor with BMP388 temp in status message for sanity check

## Parts Reference

| Component | Example Part | Notes |
|-----------|--------------|-------|
| BMP388 Breakout | Adafruit BMP388 | Or generic BMP388 module |
| DS18B20 Waterproof | HiLetgo DS18B20 Kit | Waterproof probe style |
| 4.7kΩ Resistor | 1/4W through-hole | Pull-up for DS18B20 (GP7) |
| Weather Enclosure | Stevenson screen style | Louvered for airflow, must fit Pico W |
