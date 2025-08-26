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
