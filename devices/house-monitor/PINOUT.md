# House Monitor Pinout

## Overview

The house-monitor Pico W monitors city power status, freezer temperature, and freezer door state. This is primarily a sensing device focused on safety and alerting.

## Power

- **USB Power**: Powers the Pico W (generator-backed circuit)
- **3V3 (Pin 36)**: 3.3V output for sensors
- **GND**: Ground connections

## GPIO Pin Assignments

| GPIO | Mode   | Function          | Description          | Notes                                     |
| ---- | ------ | ----------------- | -------------------- | ----------------------------------------- |
| GP2  | Input  | City Power Sense  | HIGH = power present | Pull-down, connect to RS-25-5 via divider |
| GP3  | Input  | Freezer Door Reed | LOW = door closed    | Internal pull-up enabled                  |
| GP4  | 1-Wire | DS18B20 Data      | Freezer temperature  | Requires 4.7kΩ external pull-up to 3V3    |
| GP25 | Output | Built-in LED      | Status/heartbeat     | Toggles every 30s                         |

## External Components

### City Power Detection

The Mean Well RS-25-5 power supply outputs 5V DC when city/utility power is present. Since GP2 is 3.3V logic, we need to step down the voltage.

**Option A: Voltage Divider (Simple)**

```
RS-25-5 +5V ─── [10kΩ] ──┬── GP2
                         │
                        [6.8kΩ]
                         │
RS-25-5 GND ─────────────┴── Pico GND
```

- Output: ~3.0V when 5V input (safe for GP2)
- Pros: Simple, low component count
- Cons: Direct electrical connection to mains-powered supply

**Option B: Optocoupler (Isolated, Recommended for Safety)**

```
                     ┌─────────────┐
RS-25-5 +5V ──[1kΩ]──┤ Opto LED+  │
                     │ (e.g. PC817)│
RS-25-5 GND ─────────┤ Opto LED-  │
                     └─────────────┘
                     ┌─────────────┐
Pico 3V3 ───[10kΩ]───┤ Collector  │── GP2
                     │             │
Pico GND ────────────┤ Emitter    │
                     └─────────────┘
```

- Output: HIGH when opto LED lit, LOW when off
- Pros: Galvanic isolation from mains-connected supply
- Cons: Slightly more complex

**Notes:**

- RS-25-5 must be installed by a licensed electrician
- RS-25-5 is wired to **utility side** of transfer switch
- When generator is running (utility power off), RS-25-5 has no power → GP2 reads LOW

### DS18B20 Temperature Sensor

**Connections:**
| Sensor Wire | Connect To | Notes |
|-------------|------------|-------|
| Red (VCC) | 3V3 | Power |
| Black (GND) | GND | Ground |
| Yellow/White (DATA) | GP4 | 1-Wire data |
| - | 4.7kΩ between GP4 and 3V3 | Pull-up resistor |

**Placement:**

- Place waterproof probe inside chest freezer
- Route wire through bottom door gasket corner
- Use flat Cat6 cable section to minimize seal disruption
- Secure probe with zip tie to avoid contact with freezer walls

**Long Wire Run Notes:**

- For runs over 3 meters, use 2.7kΩ pull-up instead of 4.7kΩ
- Keep wiring away from power cables to reduce interference
- If using Cat6 cable, use a single twisted pair for data + ground

### Freezer Door Reed Switch

**Connections:**
| Terminal | Connect To | Notes |
|----------|------------|-------|
| Terminal 1 | GP3 | Signal | white
| Terminal 2 | GND | Ground |blue

**Switch Characteristics:**

- Type: NO (Normally Open)
- Activation: Closes when magnet approaches
- When closed: GP3 pulled LOW (door is closed)
- When open: GP3 pulled HIGH by internal pull-up (door is open)

**Installation:**

- Mount switch on freezer door **frame** (fixed side)
- Mount magnet on **door** (moving side)
- Align so switch closes when door is fully closed
- Optimal gap: 5-10mm when door closed
- Test activation before permanent mounting

## Wiring Diagram (Cat6 Cable)

For routing DS18B20 and reed switch through flat Cat6:

### Pico W End (RJ45)

| RJ45 Pin | Wire Color (T568B) | Pico W Connection | Description      |
| -------- | ------------------ | ----------------- | ---------------- |
| 1        | White/Orange       | GP4               | DS18B20 Data     |
| 2        | Orange             | 3V3               | DS18B20 Power    |
| 3        | White/Green        | GP3               | Door Reed Switch |
| 4        | Blue               | -                 | Spare            |
| 5        | White/Blue         | -                 | Spare            |
| 6        | Green              | -                 | Spare            |
| 7        | White/Brown        | GND               | Common Ground    |
| 8        | Brown              | -                 | Spare            |

### Sensor End Connections

**DS18B20:**

- Red wire → Orange (Pin 2)
- Yellow/White wire → White/Orange (Pin 1)
- Black wire → White/Brown (Pin 7)
- 4.7kΩ resistor: Between Pin 1 and Pin 2 **at Pico end**

**Reed Switch:**

- Terminal 1 → White/Green (Pin 3)
- Terminal 2 → White/Brown (Pin 7)

### Twisted-Pair Usage

| Pair   | Pins | Function                 | Notes                              |
| ------ | ---- | ------------------------ | ---------------------------------- |
| Orange | 1,2  | DS18B20 Data + Power     | Keep together for signal integrity |
| Green  | 3,6  | Door Reed Signal + Spare |                                    |
| Blue   | 4,5  | Spare                    | Future expansion                   |
| Brown  | 7,8  | GND + Spare              |                                    |

## Installation Notes

### 1. City Power Monitor Circuit

**Requirements:**

- ⚠️ **MUST be installed by licensed electrician**
- RS-25-5 wired to **utility side** of transfer switch
- Proper gauge wire (14-16 AWG) with inline fuse
- Weatherproof enclosure if near transfer switch outdoors

**How It Works:**

1. When utility power is ON → RS-25-5 has input → Outputs 5V → GP2 reads HIGH → Status: "online"
2. When utility power is OFF (generator running) → RS-25-5 has no input → Outputs 0V → GP2 reads LOW → Status: "offline"

### 2. Freezer Sensor Placement

**Temperature Probe:**

- Place in center of freezer, not touching walls or items
- Avoid areas directly in front of cooling vents
- Use zip tie or clip to secure probe
- Test reading before final placement

**Door Seal Integrity:**

- Use flat Cat6 at bottom corner of door gasket
- Route at a point where gasket compresses least
- Test seal after installation using paper test:
  - Close door on paper at wire location
  - Paper should resist pulling out
- If frost builds at wire entry, add silicone bead

### 3. Signal Integrity

- Keep sensor wiring away from power cables (especially fluorescent lights)
- For runs over 3m:
  - Use lower pull-up (2.7kΩ)
  - Consider shielded cable
  - Keep I2C speed low (if applicable)
- All grounds should be connected together

## Verification Checklist

### Pre-Installation (Bench Test)

- [ ] DS18B20 detected on 1-Wire bus (ROM scan shows device)
- [ ] Temperature reads correctly at room temperature (~68-72°F)
- [ ] Reed switch activates when magnet approaches
- [ ] GP2 reads HIGH when 3.3V applied (simulating power)
- [ ] GP2 reads LOW when floating (pull-down active)
- [ ] 4.7kΩ pull-up resistor installed on DS18B20 data line

### Post-Installation

- [ ] DS18B20 reads correct freezer temperature (verify with thermometer)
- [ ] Temperature drops after freezer runs (sensor responding)
- [ ] Door status changes correctly when door opens/closes
- [ ] Door ajar timing works (leave door open, check incrementing)
- [ ] City power shows "online" when utility power present
- [ ] City power shows "offline" when utility power removed (test if safe)
- [ ] All MQTT topics publishing correctly
- [ ] Heartbeat publishing every 30 seconds
- [ ] No frost buildup at cable entry point (check after 24 hours)

## MQTT Topics Reference

### Consolidated Status (Published Every 30 Seconds)

**Topic:** `home/house-monitor/status`

**Payload:**

```json
{
  "timestamp": 1703789400000,
  "uptime_s": 3600,
  "health": "online",
  "power": {
    "city": "online"
  },
  "freezer": {
    "temperature_f": -5.2,
    "door": "closed",
    "door_ajar_s": 0
  },
  "errors": [],
  "memory": {
    "free": 150000,
    "allocated": 50000
  }
}
```

**Field Descriptions:**

| Field                   | Type       | Description                                       |
| ----------------------- | ---------- | ------------------------------------------------- |
| `timestamp`             | int        | Device time in ticks_ms                           |
| `uptime_s`              | int        | Seconds since boot                                |
| `health`                | string     | `"online"` or `"degraded"` (if errors present)    |
| `power.city`            | string     | `"online"` or `"offline"`                         |
| `freezer.temperature_f` | float/null | Temperature in °F, null if sensor error           |
| `freezer.door`          | string     | `"open"` or `"closed"`                            |
| `freezer.door_ajar_s`   | int        | Seconds door has been open (0 if closed)          |
| `errors`                | array      | Active errors with code, message, since timestamp |
| `memory.free`           | int        | Free memory in bytes                              |
| `memory.allocated`      | int        | Allocated memory in bytes                         |

### Bootstrap-Managed Topics

| Topic                              | Description                              |
| ---------------------------------- | ---------------------------------------- |
| `home/system/house-monitor/health` | LWT: `"offline"` when device disconnects |
| `home/system/house-monitor/sos`    | Critical bootstrap errors                |
| `home/system/house-monitor/update` | OTA update trigger (subscribe)           |

## Troubleshooting

### DS18B20 Not Found

1. Check wiring: Data→GP4, VCC→3V3, GND→GND
2. Verify 4.7kΩ pull-up between Data and 3V3
3. Try different GPIO pin (might be damaged)
4. For long runs, try stronger pull-up (2.7kΩ)
5. Check for cold solder joints

### Temperature Reading Errors

1. CRC errors: Check wiring, reduce cable length, add shielding
2. Always reads 85°C/185°F: Conversion not complete (timing issue)
3. Wildly wrong values: Pull-up resistor missing or wrong value
4. Sensor drift over time: Normal aging, may need replacement

### Reed Switch Issues

1. False triggers: Increase debounce time in code
2. Never triggers: Check magnet alignment and distance (<10mm gap)
3. Always shows closed: Check NO vs NC switch type; verify wiring
4. Intermittent: Weak magnet or excessive gap

### City Power Detection

1. Always shows online: Check pull-down configuration; verify divider values
2. Always shows offline: Check RS-25-5 output; verify divider/optocoupler
3. Flapping rapidly: Increase debounce time; check for electrical noise
4. No change when power fails: Verify RS-25-5 is on utility side (not generator side)

## Parts Reference

| Component          | Example Part           | Notes                        |
| ------------------ | ---------------------- | ---------------------------- |
| DS18B20 Waterproof | HiLetgo DS18B20 Kit    | Get the 5-pack               |
| Reed Switch        | Generic NO reed switch | Any 2-wire magnetic switch   |
| 4.7kΩ Resistor     | 1/4W through-hole      | For DS18B20 pull-up          |
| 10kΩ Resistor      | 1/4W through-hole      | For voltage divider          |
| 6.8kΩ Resistor     | 1/4W through-hole      | For voltage divider          |
| Optocoupler        | PC817 or similar       | For isolated power detection |
| Flat Cat6 Cable    | Generic flat Cat6      | For door gasket routing      |
| Mean Well RS-25-5  | RS-25-5                | 25W 5V PSU for city power    |
