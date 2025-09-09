# Active Context - IRIS

## Current Work Focus

### Immediate Priority: Bootstrap Scheduler Implementation

The project is transitioning from a basic bootstrap design to a non-blocking scheduler architecture. This is Phase 1 of the implementation plan, focusing on creating an immortal bootstrap layer that owns all system resources and provides a runtime API to applications.

### Key Transition in Progress

Moving from application-owned MQTT clients to a centralized bootstrap-owned client with message routing. This fundamental architectural change ensures the bootstrap maintains control and can recover from any application failure.

## Recent Changes (as of 2025-09-08)

### Completed Work

1. **Weather Time-Series Feature**:

   - Database queries for aggregating weather data
   - API endpoint `/api/garage/weather/history` with bucketing support
   - Android UI with temperature and pressure graphs
   - Navigation from HomeScreen weather tile to History tab

2. **UI Improvements**:

   - Garage door tile styling matches flood light tile
   - Freezer monitors arranged side-by-side
   - Removed threshold buttons from HomeScreen

3. **Alert System Enhancement**:
   - Structured current alerts via `/api/alerts/current`
   - SOS panel in mobile app consumes alert data
   - Rate-limited SOS for weather station failures

### Infrastructure in Place

- Basic bootstrap files created (`main.py`, `bootstrap_manager.py`, `http_updater.py`)
- Shared modules for WiFi, MQTT, and config management
- Deployment automation via `mpremote`
- Docker setup for server stack (Mosquitto, PostgreSQL, FastAPI)
- React Native mobile app with Material Design UI

## Next Steps (Priority Order)

### 1. Bootstrap Scheduler Loop (CRITICAL)

- [ ] Convert bootstrap to non-blocking scheduler (50-100 Hz target)
- [ ] Implement continuous MQTT pumping (`check_msg()` each iteration)
- [ ] Add WiFi/MQTT reconnection with exponential backoff
- [ ] Publish boot messages, version, and periodic health

### 2. Runtime API Implementation

- [ ] Define runtime object passed to app during `init(runtime)`
- [ ] Implement `publish()`, `subscribe()`, `unsubscribe()` methods
- [ ] Add `sos()`, `now_ms()`, and optional `log()` methods
- [ ] Enforce fast-callback budget for immediate handlers

### 3. Application Lifecycle Management

- [ ] Replace infinite-loop `main()` with plugin lifecycle
- [ ] Implement `init(runtime)`, `tick()`, `shutdown(reason)` hooks
- [ ] Add timeout handling for unresponsive apps during shutdown
- [ ] Ensure app exceptions trigger SOS but don't crash bootstrap

### 4. OTA Update Flow

- [ ] Quiesce app before update (`shutdown()` with timeout)
- [ ] Publish status progression: `update_received` → `updating` → `updated`
- [ ] Protect bootstrap files during update
- [ ] Implement temp-write then rename strategy
- [ ] Reset device after successful update

## Active Decisions & Considerations

### Architecture Decisions

1. **Single MQTT Client**: Bootstrap owns the only MQTT client, apps use runtime API
2. **Cooperative Scheduling**: Apps must return quickly from `tick()` and callbacks
3. **Fast vs Queued Callbacks**: Critical commands use fast=True, telemetry uses fast=False
4. **Bootstrap Protection**: Bootstrap files are never updated via OTA

### Implementation Patterns

- **Error Handling**: Catch all app exceptions, publish SOS, continue running
- **State Machine**: Bootstrap maintains clear states (connecting, running, updating, help)
- **Message Routing**: Bootstrap subscribes to all topics, routes to app callbacks
- **Health Reporting**: Bootstrap publishes system health, apps publish telemetry

### Testing Priorities

- Command responsiveness: < 10ms for door/light commands
- OTA resilience: System remains responsive during failed updates
- Network recovery: Automatic reconnection after broker outages
- App fault tolerance: SOS generation without system crash

## Important Patterns & Preferences

### Code Organization

- Bootstrap code is minimal and bulletproof (never changes)
- Shared modules provide reusable functionality
- Device apps follow plugin architecture pattern
- Configuration uses JSON with device-specific overrides

### MQTT Conventions

- Topic structure: `home/{area}/{device}/{metric}`
- System topics: `home/system/{device_id}/{type}`
- JSON payloads for complex data
- Retained messages for state persistence

### Development Workflow

1. Test changes locally with `mpremote`
2. Commit to Git when stable
3. Server triggers OTA via MQTT manifest
4. Monitor SOS messages for issues

## Learnings & Project Insights

### What Works Well

- Deployment script with config merging is reliable
- Docker compose for server stack simplifies development
- React Native with Expo provides rapid mobile development
- MQTT topic structure is logical and extensible

### Current Challenges

- Bootstrap scheduler implementation is complex but critical
- Balancing immediate responsiveness with cooperative multitasking
- Ensuring OTA updates don't brick devices
- Managing state synchronization between devices and server

### Key Insights

1. **Separation of Concerns**: Bootstrap/app separation is essential for reliability
2. **Fail-Safe Design**: Every failure mode needs a recovery path
3. **Human in the Loop**: SOS messages are critical for real-world deployment
4. **Progressive Enhancement**: Start simple, add complexity only when stable

## Resource References

### Key Files to Review

- `design_doc.md`: Complete system architecture
- `TASK.md`: Current task tracking and progress
- `devices/bootstrap/`: Bootstrap implementation
- `server/api/main.py`: Server API implementation
- `android/app/`: Mobile app implementation

### External Dependencies

- MicroPython for Pico W
- Mosquitto MQTT broker
- PostgreSQL database
- FastAPI for server
- React Native + Expo for mobile
- Docker for server deployment
