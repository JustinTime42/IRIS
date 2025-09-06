# Garage Controller Pinout

## Power
- **USB Power**: Powers the Pico W via onboard USB port
- **3V3**: 3.3V output for sensors
- **GND**: Ground connections

## GPIO Pin Assignments

| GPIO | Function | Description | Notes |
|------|----------|-------------|-------|
| GP2  | Output   | Garage Door Relay Control | HIGH = Activate relay |
| GP3  | Input    | Garage Door Open Reed Switch | LOW when door is open, internal pull-up |
| GP4  | Input    | Garage Door Closed Reed Switch | LOW when door is closed, internal pull-up |
| GP5  | Output   | Flood Light Relay Control | HIGH = Lights on |
| GP6  | I2C SDA  | BMP388 Temperature/Pressure Sensor | 3.3V logic |
| GP7  | I2C SCL  | BMP388 Temperature/Pressure Sensor | 3.3V logic |
| GP8  | 1-Wire   | DS18B20 Temperature Sensor | Requires 4.7kΩ pull-up |
| GP25 | Output   | Built-in LED | System status indicator |

## External Components

### Relays
- **Garage Door Relay**: 
  - Control: GP2
  - Power: 5V from USB
  - Common: Garage door button
  - NO/NC: Connect to match existing button behavior

- **Flood Light Relay**:
  - Control: GP5
  - Power: 5V from USB
  - Connect to light switch wiring

### Sensors
- **BMP388**:
  - VIN: 3.3V (power input)
  - 3Vo: (not connected, this is the 3.3V output)
  - GND: GND
  - SCK: GP7 (SCL)
  - SDO: GND (for I2C mode, pulls address low)        
  - SDI: GP6 (SDA)
  - CS: 3.3V (pulls high for I2C mode)
  - INT: (not connected, unless you want to use interrupts)

- **DS18B20**:
  - Data: GP8
  - VCC: 3.3V
  - GND: GND
  - 4.7kΩ pull-up between Data and 3.3V

### Reed Switches
- **Door Open**:
  - GP3 to switch
  - Switch to GND
  - Internal pull-up enabled
  - blue = common to gnd, white to gpio, black unused 

- **Door Closed**:
  - GP4 to switch
  - Switch to GND
  - Internal pull-up enabled
  - blue = common to gnd, white to gpio, black unused 

## Notes
- All GPIOs are 3.3V logic level
- Relays should be powered from 5V but controlled via 3.3V logic
- Use appropriate current-limiting resistors for any indicator LEDs
- Consider adding protection diodes for relay coils if not internally included

---

## Wiring Overview

- **In-enclosure wiring (short leads, soldered)**:
  - Garage Door Relay (GP2)
  - Flood Light Relay (GP5)

- **Two-conductor runs (to remote sensors)**:
  - Garage Door Reed Switches (GP3, GP4 → switch → GND)
  - Freezer Temperature Sensor (DS18B20 on GP8)
    - Default design assumes 3-wire DS18B20 (VCC, GND, DATA with 4.7kΩ pull-up to 3V3).
    - If you intend to run a 2-wire parasitic-power DS18B20, firmware changes and a strong pull-up are required. Please confirm before wiring.

- **Multi-conductor run (weather station)**:
  - CAT5 (T568B) cable from Pico to weather station enclosure for I2C sensor(s) and future expansion.

## Weather Station CAT5 Wiring (T568B)

Purpose: carry power (3V3/GND) and I2C bus (SDA GP6, SCL GP7) to the BMP388 breakout in the weather enclosure, with one spare twisted pair reserved for future sensors.

Recommended mapping (signals paired with ground to reduce noise):

| RJ45 Pin | Wire Color (T568B) | Assignment | Notes |
|---------:|---------------------|------------|-------|
| 1 | White/Orange | SCL (GP7) | I2C clock |
| 2 | Orange | GND | Pair with SCL (twisted orange pair) |
| 3 | White/Green | SDA (GP6) | I2C data |
| 4 | Blue | 3V3 | Power to sensors |
| 5 | White/Blue | GND | Power return (twisted blue pair) |
| 6 | Green | GND | Pair with SDA (twisted green pair pins 3/6) |
| 7 | White/Brown | Spare | Reserve for future sensor/IO |
| 8 | Brown | Spare | Reserve for future sensor/IO |

Notes:
- Keep I2C bus length reasonable; for CAT5 runs, target ≤5–10 m and set bus speed conservatively (100 kHz or lower) if needed.
- Ensure I2C pull-ups are present on SDA/SCL at the weather-end. Many BMP388/BMP280 breakouts include 10k pull-ups; add/adjust to ~4.7k if signal integrity requires it.
- Power budget: 3.3V over long CAT5 runs can drop; verify voltage at the sensor under load.
- BMP388 wiring recap (I2C mode) per this design: `SDI→SDA (GP6)`, `SCK→SCL (GP7)`, `SDO→GND (addr 0x76)`, `CS→3V3`, `VIN→3V3`, `GND→GND` (see Sensors section above).
 - Twisted-pair optimization summary: 1–2 (orange) = SCL+GND, 3–6 (green) = SDA+GND, 4–5 (blue) = 3V3+GND. This minimizes loop area and crosstalk.

Cable termination:
- If not using RJ45 connectors, still follow the T568B color mapping for consistency. Twist the assigned signal with its paired ground to maintain the benefits of the twisted pair.

## CAT5 Wiring - DS18B20 and Reed Switches

### Pico W End (RJ45)
| RJ45 Pin | Wire Color (T568B) | Pico W Connection | Description           |
|----------|-------------------|-------------------|-----------------------|
| 1        | White/Orange     | GP8              | DS18B20 Data          |
| 2        | Orange           | 3.3V             | Power for DS18B20     |
| 3        | White/Green      | GP3              | Door Open Reed Switch |
| 4        | Blue             | GP4              | Door Closed Reed Switch |
| 5        | White/Blue       | -                | Not connected         |
| 6        | Green            | -                | Not connected         |
| 7        | White/Brown      | GND              | Ground for all sensors|
| 8        | Brown            | -                | Not connected         |

### Sensor End
#### DS18B20 Temperature Sensor
- **Red (VCC)**: Connect to Orange (Pin 2)
- **Yellow (DATA)**: Connect to White/Orange (Pin 1)
- **Black (GND)**: Connect to White/Brown (Pin 7)
- **4.7kΩ Resistor**: Between Orange (Pin 2) and White/Orange (Pin 1)

#### Door Open Reed Switch
- **One side**: Connect to White/Green (Pin 3)
- **Other side**: Connect to White/Brown (Pin 7, GND)

#### Door Closed Reed Switch
- **One side**: Connect to Blue (Pin 4)
- **Other side**: Connect to White/Brown (Pin 7, GND)

### Notes:
1. The DS18B20 requires a 4.7kΩ pull-up resistor between the data line and 3.3V.
2. The reed switches are normally open and will close when near a magnet.
3. The internal pull-up resistors on GP3 and GP4 will be enabled in software.
4. The unused pairs (pins 5,6,8) are left for future expansion.
5. Keep the sensor cable run as short as possible for best results with the DS18B20.
6. All ground connections (White/Brown) should be tied together at the sensor end.

### Twisted-Pair Usage
- **Pair 1 (Orange)**: DS18B20 Data + 3.3V (with pull-up resistor)
- **Pair 2 (Green)**: Door Open Reed Switch + unused
- **Pair 3 (Blue)**: Door Closed Reed Switch + unused
- **Pair 4 (Brown)**: GND + unused

This wiring maintains signal integrity by keeping signal pairs twisted and provides proper power distribution.
