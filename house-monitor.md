# House Monitor Pico W - Complete Implementation Plan

## Executive Summary

The **house-monitor** Pico W is the second device in the Corvids Nest home automation system. It monitors critical infrastructure including city power status, freezer temperature, and freezer door state. This is a **passive monitoring device** - no interactive controls - so it uses a **consolidated status message** published every 30 seconds rather than multiple real-time topics.

---

## 1. Device Overview

### 1.1 Purpose and Functions

| Function                   | Description                         | Alert Conditions                    |
| -------------------------- | ----------------------------------- | ----------------------------------- |
| **City Power Monitoring**  | Detects utility power presence      | Alert when power fails              |
| **Freezer Temperature**    | Monitors chest freezer in kitchen   | Alert if temp > 10°F for 5+ minutes |
| **Freezer Door Detection** | Reed switch on upright freezer door | Alert if door open > 5 minutes      |

### 1.2 Location and Power

- **Physical Location**: Near upright freezer in kitchen/utility area
- **Power Source**: Generator-backed circuit (critical for continuous monitoring)
- **City Power Detection**: Separate Mean Well RS-25-5 PSU on utility side of transfer switch

### 1.3 Device Identity

- **device_id**: `house-monitor`
- **MQTT Client ID**: Derived from Pico W unique hardware ID (handled by bootstrap)

---

## 2. Consolidated Status Architecture

### 2.1 Design Philosophy

Since all monitoring on this device is **passive** (no user-interactive controls), we use a single consolidated status message every 30 seconds instead of multiple separate topics. This approach:

- **Simplifies code**: One publish cycle instead of tracking multiple timers
- **Provides atomic snapshots**: All sensor data is consistent within each message
- **Reduces MQTT traffic**: One message instead of 5-6 separate publishes
- **Enables server-side change detection**: Server compares consecutive messages
- **Improves failure visibility**: Missing/null values are explicit in each message

### 2.2 Status Message Format

**Topic:** `home/house-monitor/status`

**Payload (every 30 seconds):**

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

### 2.3 Field Descriptions

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

### 2.4 Error Object Format

When errors occur, they're tracked in the `errors` array:

```json
{
  "errors": [
    {
      "code": "ds18b20_read_error",
      "message": "CRC mismatch on read",
      "since": 1703789100000
    }
  ]
}
```

Errors are **added** when problems occur and **cleared** when resolved. Server-side alerting can escalate if errors persist across multiple consecutive messages.

### 2.5 Comparison: Old vs New Approach

| Aspect              | Old (Multiple Topics)          | New (Consolidated)        |
| ------------------- | ------------------------------ | ------------------------- |
| Topics per device   | 6-8                            | 1                         |
| Messages per minute | 10+                            | 2                         |
| State consistency   | Possible race conditions       | Atomic snapshot           |
| Code complexity     | Multiple timers, rate limiters | Single publish loop       |
| Failure detection   | Timeout per topic              | Null values explicit      |
| Server processing   | Correlate multiple topics      | Single message per device |

---

## 3. Hardware Requirements

### 3.1 Components List

| Component                  | Qty    | Purpose              | Notes                           |
| -------------------------- | ------ | -------------------- | ------------------------------- |
| Raspberry Pi Pico W        | 1      | Main controller      | Generator-backed power          |
| Mean Well RS-25-5 5V PSU   | 1      | City power detection | Utility-side power              |
| HiLetgo DS18B20 waterproof | 1      | Freezer temperature  | From existing pack              |
| Reed switch (magnetic)     | 1      | Door ajar detection  | NO type, for upright freezer    |
| 4.7kΩ resistor             | 1      | DS18B20 pull-up      | May need 2.7kΩ for long runs    |
| 10kΩ + 6.8kΩ resistors     | 1 each | Voltage divider      | For city power (or optocoupler) |
| Flat Cat6 cable            | ~10ft  | Door seal routing    | Ribbon-style for gasket         |
| Project enclosure          | 1      | Device housing       | Ventilated, food-safe area      |

### 3.2 City Power Monitor Design

The city power detection is elegantly simple:

1. Mean Well RS-25-5 PSU is hardwired to **utility side** of transfer switch
2. This PSU provides a 5V signal stepped down via voltage divider to ~3V
3. When city power is present, GP2 reads HIGH
4. When city power fails, GP2 reads LOW (pull-down default)

### 3.3 Freezer Sensor Design

**Temperature Sensor (DS18B20)**:

- Waterproof probe placed inside chest freezer
- Cat6 cable routed through bottom door gasket corner
- 4.7kΩ pull-up resistor at Pico W end

**Door Reed Switch**:

- Mounted on upright freezer door frame
- Magnet on door, switch on frame
- NO (Normally Open) - closes when door closed

---

## 4. GPIO Pin Assignments

| GPIO | Mode   | Function          | Description               | Notes                            |
| ---- | ------ | ----------------- | ------------------------- | -------------------------------- |
| GP2  | Input  | City Power Sense  | HIGH = City power present | Pull-down, voltage divider input |
| GP3  | Input  | Freezer Door Reed | LOW = Door closed         | Internal pull-up enabled         |
| GP4  | 1-Wire | DS18B20 Data      | Freezer temperature       | Requires 4.7kΩ external pull-up  |
| GP25 | Output | Built-in LED      | Status indicator          | Toggles every 30s on publish     |

---

## 5. MQTT Architecture

### 5.1 Published Topics

| Topic                       | Frequency | Description              |
| --------------------------- | --------- | ------------------------ |
| `home/house-monitor/status` | Every 30s | Consolidated status JSON |

### 5.2 Bootstrap-Managed Topics

| Topic                              | Description                            |
| ---------------------------------- | -------------------------------------- |
| `home/system/house-monitor/health` | LWT: "offline" when device disconnects |
| `home/system/house-monitor/sos`    | Critical bootstrap errors              |
| `home/system/house-monitor/update` | OTA update trigger (subscribed)        |

### 5.3 Server-Side Processing

The server subscribes to `home/house-monitor/status` and:

1. **Stores each message** in time-series database (one row per status)
2. **Compares to previous** to detect state changes for logging
3. **Evaluates alert conditions**:
   - `freezer.temperature_f > 10` for consecutive messages → alert
   - `freezer.door_ajar_s > 300` → alert
   - `power.city == "offline"` → immediate alert
   - `errors` array non-empty for 2+ messages → escalate
4. **Detects device offline** if no message received for 90+ seconds

---

## 6. Software Architecture

### 6.1 Module Structure

```
devices/house-monitor/
├── app/
│   ├── __init__.py          # Package marker
│   ├── main.py              # Application entry point (init/tick/shutdown)
│   └── sensors.py           # Sensor utilities (unchanged)
└── PINOUT.md                # Hardware documentation
```

### 6.2 Application Flow

```
                    ┌─────────────┐
                    │   BOOT      │
                    └──────┬──────┘
                           │ init(runtime)
                           ▼
    ┌──────────────────────────────────────┐
    │             RUNNING                   │
    │  ┌─────────────────────────────────┐ │
    │  │ tick() every ~20ms              │ │
    │  │ - Update debounced states       │ │
    │  │ - Manage async temp conversion  │ │
    │  │ - Every 30s: publish status     │ │
    │  └─────────────────────────────────┘ │
    └──────────────────────────────────────┘
```

### 6.3 Timing Strategy

| Task            | Timing      | Notes                                |
| --------------- | ----------- | ------------------------------------ |
| Power debounce  | 100ms       | Filters electrical noise             |
| Door debounce   | 50ms        | Filters mechanical bounce            |
| Temp conversion | 800ms async | Non-blocking, started before publish |
| Status publish  | 30,000ms    | Consolidated message                 |
| LED toggle      | On publish  | Visual heartbeat                     |
| GC collect      | On publish  | Memory cleanup                       |

### 6.4 Non-Blocking Temperature Read

The DS18B20 requires ~750ms for conversion. The code manages this asynchronously:

1. **Before publish cycle**: Start conversion
2. **During tick loops**: Wait for conversion time
3. **At publish time**: Read result, include in status

```python
# Simplified flow
if not temp_converting and not temp_ready:
    start_conversion()

if temp_converting and elapsed >= 800ms:
    read_result()
    temp_ready = True

if time_to_publish and temp_ready:
    publish_status()
    temp_ready = False
```

---

## 7. Error Handling

### 7.1 Error Tracking

Errors are tracked as objects in an array, not separate SOS messages:

```python
def _add_error(self, code: str, message: str):
    if not already_tracked(code):
        self._errors.append({
            "code": code,
            "message": message,
            "since": time.ticks_ms()
        })

def _clear_error(self, code: str):
    self._errors = [e for e in self._errors if e["code"] != code]
```

### 7.2 Error Codes

| Code                    | Trigger                     | Auto-Clear              |
| ----------------------- | --------------------------- | ----------------------- |
| `power_pin_init_failed` | GPIO init failure           | No (requires reboot)    |
| `door_pin_init_failed`  | GPIO init failure           | No                      |
| `ds18b20_not_found`     | No sensors on bus           | No                      |
| `ds18b20_init_failed`   | OneWire init error          | No                      |
| `ds18b20_read_error`    | CRC/read failure            | Yes, on successful read |
| `temp_out_of_range`     | Value outside -50°F to 50°F | Yes, on valid read      |

### 7.3 Health Status

- `"online"` - No errors, all sensors working
- `"degraded"` - One or more errors present

Server-side escalation: If `health == "degraded"` for 3+ consecutive messages (90+ seconds), send notification.

---

## 8. Server-Side Alert Logic

With consolidated messages, alert logic becomes straightforward:

```python
# Pseudocode for server alert processing
def process_status(device_id, current, previous):
    alerts = []

    # Temperature alert: sustained high temp
    if current.freezer.temperature_f and current.freezer.temperature_f > 10:
        if previous and previous.freezer.temperature_f > 10:
            alerts.append("Freezer temperature critical: {:.1f}°F".format(
                current.freezer.temperature_f))

    # Door ajar alert: open too long
    if current.freezer.door_ajar_s > 300:  # 5 minutes
        alerts.append("Freezer door open for {} minutes".format(
            current.freezer.door_ajar_s // 60))

    # Power outage: immediate alert
    if current.power.city == "offline":
        if not previous or previous.power.city == "online":
            alerts.append("City power outage detected")

    # Device health degraded
    if current.health == "degraded" and len(current.errors) > 0:
        for error in current.errors:
            alerts.append("Device error: {} - {}".format(
                error.code, error.message))

    return alerts
```

---

## 9. Testing Procedures

### 9.1 Bench Testing

1. **Basic Boot Test**

   - Flash bootstrap + app to Pico W
   - Verify MQTT connection
   - Check status messages arriving every 30s

2. **Status Message Validation**

   - Subscribe to `home/house-monitor/status`
   - Verify JSON structure matches spec
   - Check all fields populated correctly

3. **Sensor Tests**

   - DS18B20: Verify temperature reads, test with ice water
   - Reed switch: Verify door open/closed detection
   - City power: Apply/remove 3.3V to GP2

4. **Error Handling**
   - Disconnect DS18B20, verify `temperature_f: null` and error in array
   - Reconnect, verify error clears on next successful read

### 9.2 Integration Testing

1. **Server Integration**

   - Verify server receives and parses status messages
   - Test alert conditions trigger correctly
   - Verify device offline detection (stop device, wait 90s)

2. **State Change Detection**
   - Open door, verify `door_ajar_s` increments each message
   - Simulate power outage, verify state change detected

---

## 10. Implementation Checklist

### Phase 1: Code Development

- [x] Create `devices/house-monitor/app/main.py` (consolidated approach)
- [x] Create `devices/house-monitor/app/sensors.py`
- [x] Create `devices/house-monitor/app/__init__.py`
- [x] Create `devices/house-monitor/PINOUT.md`

### Phase 2: Hardware Prep

- [ ] Gather components (Pico W, DS18B20, reed switch, resistors)
- [ ] Build voltage divider or optocoupler for city power
- [ ] Prepare Cat6 cables with proper lengths
- [ ] Test DS18B20 on breadboard

### Phase 3: Bench Testing

- [ ] Flash bootstrap to Pico W
- [ ] Deploy house-monitor app
- [ ] Verify MQTT connectivity
- [ ] Validate status message format
- [ ] Test all sensor readings
- [ ] Test error tracking and clearing

### Phase 4: Electrician Work

- [ ] Install Mean Well RS-25-5 on utility side of transfer switch
- [ ] Wire RS-25-5 to connection point near Pico W location
- [ ] Test RS-25-5 output (5V when utility on, 0V when off)

### Phase 5: Field Installation

- [ ] Mount Pico W enclosure near freezer
- [ ] Route Cat6 through door gasket
- [ ] Install DS18B20 probe in freezer
- [ ] Install door reed switch and magnet
- [ ] Connect city power detection circuit
- [ ] Power up and verify status messages

### Phase 6: Server Integration

- [ ] Update server to subscribe to `home/house-monitor/status`
- [ ] Implement alert logic for consolidated messages
- [ ] Configure alert thresholds
- [ ] Test end-to-end alerting
- [ ] Monitor for 24-48 hours for stability

---

## 11. Future Considerations

### 11.1 Applying to Garage Controller

The garage-controller has **interactive controls** (door, light) that need real-time feedback. Recommended hybrid approach:

```
# Real-time (on-change) - for UI responsiveness
home/garage/door/status    → "open"/"closed"/"opening"/"closing"
home/garage/light/status   → "on"/"off"

# Consolidated (every 30s) - for logging/alerting
home/garage-controller/status → { door, light, weather, freezer, errors, ... }
```

### 11.2 Benefits of Standardization

If both devices use consolidated status:

- **Uniform server processing**: Same code handles all device status
- **Consistent database schema**: One table structure for all devices
- **Simplified alerting**: Same pattern for all passive monitoring
- **Easier debugging**: Full device state in single message

---

## Appendix A: Complete Status Message Example

```json
{
  "timestamp": 1703789400000,
  "uptime_s": 86400,
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
    "free": 148576,
    "allocated": 52896
  }
}
```

## Appendix B: Example with Active Error

```json
{
  "timestamp": 1703789430000,
  "uptime_s": 86430,
  "health": "degraded",
  "power": {
    "city": "online"
  },
  "freezer": {
    "temperature_f": null,
    "door": "open",
    "door_ajar_s": 45
  },
  "errors": [
    {
      "code": "ds18b20_read_error",
      "message": "CRC mismatch",
      "since": 1703789400000
    }
  ],
  "memory": {
    "free": 147200,
    "allocated": 54272
  }
}
```

---

This implementation plan reflects the consolidated status approach for passive monitoring devices, significantly simplifying both device-side and server-side code while providing complete visibility into device state.
