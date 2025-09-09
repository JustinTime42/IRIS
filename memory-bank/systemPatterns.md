# System Patterns - IRIS

## System Architecture Overview

### Hub-and-Spoke MQTT Architecture

The system uses a centralized MQTT broker on the Linux server as the communication hub. All devices connect as spokes, publishing telemetry and subscribing to commands. This pattern provides:

- Single point of truth for all communication
- Simplified debugging and monitoring
- Easy addition of new devices
- Natural message routing and filtering

### Two-Tier Device Architecture

#### Tier 1: Immortal Bootstrap Layer

```
Bootstrap (Never Updated)
├── main.py                 # Entry point, minimal
├── bootstrap_manager.py     # Scheduler and lifecycle
└── http_updater.py         # OTA update handler
```

**Key Characteristics:**

- Owns all system resources (WiFi, MQTT, hardware)
- Never yields control indefinitely
- Catches all exceptions and continues
- Provides runtime API to applications

#### Tier 2: Application Layer

```
Application (Updated via OTA)
├── app/
│   ├── main.py            # Plugin with init/tick/shutdown
│   └── sensors.py         # Device-specific logic
└── shared/                # Reusable modules
```

**Key Characteristics:**

- Cooperative plugin, not standalone program
- Uses runtime API for all system interaction
- Returns quickly from all calls
- Can be replaced without affecting bootstrap

## Key Technical Decisions

### Single MQTT Client Architecture

**Decision**: Bootstrap owns the only MQTT client on each device.

**Rationale**:

- Prevents resource conflicts
- Ensures bootstrap can always communicate
- Simplifies message routing
- Enables clean OTA updates

**Implementation**:

```python
# Bootstrap provides runtime API
runtime.publish(topic, payload, retain=False)
runtime.subscribe(topic, callback, fast=False)
runtime.unsubscribe(topic)
```

### Non-Blocking Scheduler Loop

**Decision**: Bootstrap runs a tight loop at 50-100 Hz.

**Pattern**:

```python
while True:
    update_led_state()
    ensure_wifi_connected()
    ensure_mqtt_connected()
    pump_mqtt_messages()
    publish_periodic_health()
    call_app_tick()
    # Total iteration: 10-20ms
```

**Benefits**:

- Immediate command response
- Continuous connectivity monitoring
- Regular health reporting
- Predictable timing

### Cooperative Multitasking

**Decision**: Applications must cooperate, not block.

**Rules**:

1. `tick()` must return within 50ms
2. Fast callbacks must complete in < 5ms
3. Slow work goes in queue for next `tick()`
4. No infinite loops in app code

### OTA Update Strategy

**Decision**: HTTP-based updates from GitHub, bootstrap-controlled.

**Flow**:

1. Server publishes manifest to MQTT
2. Bootstrap receives and acknowledges
3. Bootstrap quiesces app (`shutdown()`)
4. HTTP download of new files
5. Write to temp, rename to final
6. Reset device to load new code

**Safety Mechanisms**:

- Bootstrap files protected from updates
- Temp-write prevents partial files
- SOS on failure, bootstrap continues
- Timeout on app shutdown

## Design Patterns in Use

### Plugin Architecture Pattern

Applications are plugins with defined lifecycle:

```python
class Application:
    def init(self, runtime):
        """Initialize hardware and subscriptions"""
        self.runtime = runtime
        self.setup_hardware()
        self.subscribe_to_topics()

    def tick(self):
        """Called frequently, must return quickly"""
        self.read_sensors()
        self.publish_telemetry()

    def shutdown(self, reason):
        """Clean shutdown for update or reset"""
        self.cleanup_hardware()
        self.save_state()
```

### Runtime Facade Pattern

Bootstrap provides a simplified interface to system resources:

```python
class Runtime:
    def publish(self, topic, payload, retain=False): ...
    def subscribe(self, topic, callback, fast=False): ...
    def unsubscribe(self, topic): ...
    def sos(self, error, message=""): ...
    def now_ms(self): ...
    def log(self, level, msg): ...
```

### Message Router Pattern

Bootstrap routes MQTT messages to appropriate handlers:

```python
class MessageRouter:
    def __init__(self):
        self.system_handlers = {}  # Bootstrap handlers
        self.app_handlers = {}     # App subscriptions

    def dispatch(self, topic, payload):
        # System topics first
        if topic.startswith("home/system/"):
            self.handle_system(topic, payload)
        # Then app topics
        elif topic in self.app_handlers:
            self.dispatch_to_app(topic, payload)
```

### State Machine Pattern

Bootstrap maintains clear operational states:

```
STATES:
├── INIT         # Starting up
├── CONNECTING   # WiFi/MQTT connection
├── RUNNING      # Normal operation
├── UPDATING     # OTA in progress
└── HELP         # SOS mode, needs intervention
```

## Component Relationships

### Bootstrap ↔ Application

- Bootstrap owns and manages application lifecycle
- Application receives runtime API during init
- All app operations go through runtime
- Bootstrap catches all app exceptions

### Device ↔ Server

- Devices publish telemetry and status
- Server sends commands and updates
- All communication via MQTT topics
- Server tracks device health via LWT

### Server Components

```
┌─────────────────────────────────────┐
│           FastAPI Server            │
├─────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────┐ │
│  │   API   │  │ Alerts  │  │ OTA │ │
│  └────┬────┘  └────┬────┘  └──┬──┘ │
│       └────────────┼───────────┘    │
│                    ▼                 │
│           ┌────────────────┐        │
│           │   PostgreSQL   │        │
│           └────────────────┘        │
│                    ▲                 │
│                    │                 │
│           ┌────────────────┐        │
│           │   Mosquitto    │        │
│           └────────────────┘        │
└─────────────────────────────────────┘
```

### Mobile App Architecture

```
React Native App
├── Providers (Theme, Query, Navigation)
├── Navigation (Tab-based)
├── Screens (Home, Devices, Settings)
├── Hooks (useGarage, useWeather, etc.)
├── Services (API client)
└── Components (Tiles, Charts, Controls)
```

## Critical Implementation Paths

### Command Path (Fast)

1. User taps button in app
2. App sends REST request to server
3. Server publishes MQTT command
4. Bootstrap receives and routes immediately
5. App callback executes (fast=true)
6. Hardware action occurs
7. Status update published
   **Target: < 100ms end-to-end**

### Telemetry Path (Regular)

1. App `tick()` reads sensors
2. App publishes via runtime API
3. Bootstrap sends to MQTT broker
4. Server receives and stores in DB
5. Server checks alert thresholds
6. Mobile app queries API for display
   **Frequency: Every 30-60 seconds**

### OTA Update Path (Managed)

1. Developer commits code to GitHub
2. Server generates manifest from repo
3. Server publishes to device MQTT topic
4. Bootstrap orchestrates update
5. Device resets with new code
6. Bootstrap publishes success status
   **Duration: 2-5 minutes typical**

### Error Recovery Path

1. Exception occurs in app code
2. Bootstrap catches exception
3. SOS message published with details
4. Bootstrap continues scheduler loop
5. Server logs SOS, creates alert
6. Mobile app shows SOS notification
7. Device remains updateable
   **Recovery: Immediate continuation**

## Architectural Invariants

### Bootstrap Invariants

1. Bootstrap code is never modified via OTA
2. Scheduler loop never blocks indefinitely
3. MQTT client is never released to app
4. All exceptions are caught and handled
5. Device always remains updatable

### Application Invariants

1. Apps never create their own MQTT clients
2. Apps never access hardware directly
3. Apps must handle shutdown requests
4. Apps cannot prevent OTA updates
5. Apps must cooperate with scheduler

### System Invariants

1. Every device has unique device_id
2. All communication goes through MQTT
3. Server is single source of truth
4. Alerts require human acknowledgment
5. Bootstrap always recovers from failures

## Scalability Considerations

### Device Scalability

- Each device operates independently
- No inter-device dependencies
- Bootstrap overhead is minimal
- Apps can be optimized per device

### Server Scalability

- PostgreSQL handles time-series data
- MQTT broker supports thousands of clients
- API can be load-balanced
- Alerts can be queued and batched

### Network Scalability

- MQTT QoS levels for reliability
- Topic hierarchy enables filtering
- Retained messages reduce traffic
- Local buffering during outages
