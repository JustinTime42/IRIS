# Garage Controller Pinout

## Overview

The garage-controller Pico W controls the garage door, flood light, and monitors the chest freezer temperature:
- **Door Relay (GP2)**: Activates garage door opener
- **Reed Switches (GP3, GP4)**: Monitor door open/closed state
- **Flood Light Relay (GP5)**: Controls exterior flood light
- **DS18B20 (GP6)**: Freezer temperature monitoring (via CAT5 cable to chest freezer)

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
| GP5  | Output   | Flood Light Relay Control | Active-low (LOW = lights on) |
| GP6  | 1-Wire   | DS18B20 Data | Freezer temperature (via CAT5), requires 4.7kΩ pull-up |
| GP25 | Output   | Built-in LED | System status indicator |

## External Components

### Relays

**Garage Door Relay:**
- Control: GP2
- Power: 5V from USB
- Common: Garage door button
- NO/NC: Connect to match existing button behavior
- Logic: Active-high (HIGH = pulse relay)

**Flood Light Relay:**
- Control: GP5
- Power: 5V from USB
- Connect to light switch wiring
- Logic: Active-low (LOW = lights on)

### Reed Switches

**Door Open Switch:**
- GP3 to switch terminal
- Other switch terminal to GND
- Internal pull-up enabled
- Wire colors: blue = common to GND, white to GPIO, black unused

**Door Closed Switch:**
- GP4 to switch terminal
- Other switch terminal to GND
- Internal pull-up enabled
- Wire colors: blue = common to GND, white to GPIO, black unused

### DS18B20 Temperature Sensor (Freezer - GP6)

Monitors the chest freezer temperature via a CAT5 cable run from the garage controller to the freezer location.

**Connections at Pico W:**
| Signal | Connect To | Notes |
|--------|------------|-------|
| DATA | GP6 | 1-Wire data line |
| VCC | 3V3 | 3.3V power |
| GND | GND | Ground |
| Pull-up | 4.7kΩ between GP6 and 3V3 | Required for 1-Wire |

**Sensor End (at Freezer):**
| Sensor Wire | Connect To | Notes |
|-------------|------------|-------|
| Red (VCC) | VCC from CAT5 | Power |
| Black (GND) | GND from CAT5 | Ground |
| Yellow/White (DATA) | DATA from CAT5 | 1-Wire data |

**Placement:**
- Place waterproof probe inside chest freezer
- Route wire through bottom door gasket corner
- Secure probe with zip tie to avoid contact with freezer walls

## Notes

- All GPIOs are 3.3V logic level
- Relays should be powered from 5V but controlled via 3.3V logic
- Consider adding protection diodes for relay coils if not internally included

---

## Wiring Overview

```
GARAGE
┌───────────────────────────────────────────────────────────┐
│                                                            │
│    ┌──────────────────────────────────────────────────┐   │
│    │           Pico W (garage-controller)              │   │
│    │                                                   │   │
│    │  GP2 → Door Relay (to garage door opener)        │   │
│    │  GP3 ← Door Open Reed Switch                     │   │
│    │  GP4 ← Door Closed Reed Switch                   │   │
│    │  GP5 → Flood Light Relay                         │   │
│    │  GP6 ← DS18B20 freezer (via CAT5)               │   │
│    │                                                   │   │
│    └─────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│                          │ CAT5 cable                       │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │    Chest Freezer     │
                │       DS18B20        │
                │    (inside temp)     │
                └──────────────────────┘
```

**In-enclosure wiring (short leads, soldered):**
- Garage Door Relay (GP2)
- Flood Light Relay (GP5)
- 4.7kΩ pull-up resistor for DS18B20 (GP6 to 3V3)

**Two-conductor runs (to reed switches):**
- Garage Door Reed Switches (GP3, GP4 → switch → GND)

**CAT5 run (to freezer):**
- DS18B20 Freezer Sensor (GP6, 3V3, GND)

---

## CAT5 Wiring - Reed Switches

If using CAT5 cable to route reed switch connections:

### Pico W End (RJ45)

| RJ45 Pin | Wire Color (T568B) | Pico W Connection | Description |
|----------|-------------------|-------------------|-------------|
| 3 | White/Green | GP3 | Door Open Reed Switch |
| 4 | Blue | GP4 | Door Closed Reed Switch |
| 7 | White/Brown | GND | Ground for switches |

### Sensor End

**Door Open Reed Switch:**
- One side: Connect to White/Green (Pin 3)
- Other side: Connect to White/Brown (Pin 7, GND)

**Door Closed Reed Switch:**
- One side: Connect to Blue (Pin 4)
- Other side: Connect to White/Brown (Pin 7, GND)

### Notes

1. Reed switches are normally open and close when near a magnet
2. Internal pull-up resistors on GP3 and GP4 are enabled in software
3. All ground connections (White/Brown) should be tied together at the sensor end

---

## CAT5 Wiring - Freezer DS18B20

The DS18B20 only needs 3 wires, so CAT5 is overkill but works well for the run to the chest freezer.

### Recommended Wire Assignments (T568B Colors)

| Signal | Wire Color | Notes |
|--------|------------|-------|
| DATA | White/Blue | To GP6 |
| VCC | White/Brown | To 3V3 |
| GND | Blue + Brown | Tie together for lower impedance |

### Pico W End

```
3V3 (Pin 36) ────────────────── White/Brown
GND ─────────────────────────── Blue + Brown (both tied together)
GP6 (DS18B20 data) ──────────── White/Blue

Pull-up resistor: 4.7kΩ between White/Blue and 3V3
```

### Freezer End

```
DS18B20 Red (VCC) ────────────── White/Brown
DS18B20 Black (GND) ──────────── Blue + Brown (both tied together)
DS18B20 Yellow/White (DATA) ──── White/Blue
```

### Cable Length Guidelines

| Length | Expected Result |
|--------|-----------------|
| Under 3 meters | No issues with 4.7kΩ pull-up |
| 3-10 meters | Should work fine, may use 2.7kΩ pull-up if issues |
| 10+ meters | Consider stronger pull-up (2.2kΩ) or slew rate limiting |

### Important Notes

1. **4.7kΩ pull-up must be at the Pico W end** (between GP6 and 3V3)
2. **Tie both ground wires together** at each end for low impedance
3. **Keep away from high-current AC wiring** to minimize interference
4. **Route cable away from sources of electrical noise** (motors, compressors)
5. **Unused CAT5 pairs can be left disconnected** or tied to ground for shielding

---

## MQTT Topics Reference

### Door Control

| Topic | Direction | Description |
|-------|-----------|-------------|
| `home/garage/door/status` | Publish | Door state: open/closed/opening/closing/error |
| `home/garage/door/command` | Subscribe | Commands: open/close/toggle |

### Light Control

| Topic | Direction | Description |
|-------|-----------|-------------|
| `home/garage/light/status` | Publish | Light state: on/off |
| `home/garage/light/command` | Subscribe | Commands: on/off/toggle |

### Freezer Temperature

| Topic | Direction | Description | Format |
|-------|-----------|-------------|--------|
| `home/garage-controller/freezer/temperature` | Publish | Freezer temperature | Float string, °F (e.g., "-5.2") |

### Status

| Topic | Description |
|-------|-------------|
| `home/garage-controller/status` | Consolidated status (every 30s) |
| `home/system/garage-controller/health` | LWT: offline when disconnected |
| `home/system/garage-controller/sos` | Critical errors |

### Consolidated Status Payload

**Topic:** `home/garage-controller/status`

**Payload:**
```json
{
  "timestamp": 1703789400000,
  "uptime_s": 3600,
  "health": "online",
  "door": {
    "state": "closed",
    "open_switch": false,
    "closed_switch": true
  },
  "light": {
    "state": "off"
  },
  "freezer": {
    "temperature_f": -5.2
  },
  "errors": [],
  "memory": {
    "free": 150000,
    "allocated": 50000
  }
}
```

---

## Troubleshooting

### Door State Issues

1. **Always shows "error"**: Both reed switches activated simultaneously - check alignment
2. **Stuck in "opening"/"closing"**: Door stopped mid-travel or reed switch misaligned
3. **Wrong state**: Verify switch is normally-open and closes when magnet approaches

### Relay Issues

1. **Door doesn't respond**: Check relay wiring, verify 500ms pulse is sufficient
2. **Light won't turn on**: Check active-low configuration, verify relay clicks
3. **Intermittent operation**: Check relay coil power supply, add flyback diode

### DS18B20 Not Found (Freezer)

1. Check CAT5 wiring at both ends matches the pinout above
2. Verify 4.7kΩ pull-up is installed between GP6 and 3V3 at Pico W end
3. Check device logs for "DS18B20 freezer initialized" message
4. Test continuity of CAT5 cable (especially DATA line)
5. Check for cold solder joints or loose connections at both ends

### DS18B20 Temperature Reading Errors

1. **CRC errors**: Check wiring, may need stronger pull-up for long cable
2. **Always reads 85°C/185°F**: Conversion not complete (timing issue)
3. **Wildly wrong values**: Pull-up resistor missing or wrong value
4. **Intermittent readings**: Check cable connections, may have noise pickup
5. **Try a stronger pull-up**: For long runs, try 2.7kΩ or 2.2kΩ instead of 4.7kΩ

### Cable Run Issues

1. **Sensor works on short cable but not CAT5**: Likely pull-up too weak for cable capacitance
2. **Readings are noisy**: Route cable away from AC power lines
3. **Sensor stops working randomly**: Check for intermittent connection at crimp or splice

---

## Verification Checklist

### Pre-Installation (Bench Test)

- [ ] Door relay clicks when GP2 goes HIGH
- [ ] Door open reed switch (GP3) reads LOW when magnet present
- [ ] Door closed reed switch (GP4) reads LOW when magnet present
- [ ] Flood light relay activates when GP5 goes LOW
- [ ] DS18B20 freezer (GP6) detected on 1-Wire bus
- [ ] DS18B20 freezer temperature reads correctly at room temperature
- [ ] 4.7kΩ pull-up resistor installed on GP6
- [ ] WiFi connects successfully
- [ ] MQTT publishes to correct topics

### Post-Installation

- [ ] Door state changes correctly as door moves
- [ ] Door commands work via MQTT
- [ ] Flood light toggles correctly
- [ ] DS18B20 freezer reads correct freezer temperature
- [ ] CAT5 cable to freezer is secured and routed safely
- [ ] All MQTT topics publishing correctly
- [ ] Status publishing every 30 seconds

---

## Parts Reference

| Component | Example Part | Notes |
|-----------|--------------|-------|
| Garage Door Relay | SRD-05VDC-SL-C | 5V coil, 10A contacts |
| Flood Light Relay | SRD-05VDC-SL-C | 5V coil, match load |
| Reed Switch | Generic NO reed | 2-wire magnetic switch |
| DS18B20 Waterproof | HiLetgo DS18B20 Kit | Waterproof probe for freezer |
| 4.7kΩ Resistor | 1/4W through-hole | Pull-up for DS18B20 (GP6) |
| CAT5/CAT5e Cable | Any solid-core CAT5 | For freezer sensor run |
