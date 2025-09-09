# TASK.md

## Purpose

Tracks current tasks, backlog, and sub-tasks for the Home Automation System project.  
Prompt to AI: "Update TASK.md to mark XYZ as done and add ABC as a new task."  
The LLM can automatically update and create tasks as needed.

---

## Milestones

- [ ] Phase 1: Bootstrap Infrastructure
- [ ] Phase 2: Device Integration
- [ ] Phase 3: Production Deployment
- [ ] Phase 4: Advanced Features

---

## Active Tasks

### Phase 1: Bootstrap Infrastructure

#### Bootstrap Layer Development
- [ ] Implement immortal bootstrap code
  - [x] Create `main.py` bootstrap entry point
  - [ ] Implement `bootstrap_manager.py` with error handling
  - [ ] Implement WiFi connection management
  - [ ] Implement MQTT connection and subscription handling
  - [ ] Add application lifecycle management
  - [ ] Implement error recovery mechanisms
  - [ ] Add comprehensive test coverage

- [ ] Implement HTTP updater
  - [x] Create `http_updater.py` for GitHub API integration
  - [ ] Implement selective file download system
  - [ ] Add update verification and validation
  - [ ] Add error handling for network issues
  - [ ] Add test coverage for update scenarios

#### Bootstrap Scheduler & Runtime API (2025-09-07)
- [ ] Convert bootstrap to a non-blocking scheduler that never yields control indefinitely
  - [ ] Ensure continuous MQTT pumping (`check_msg()` each loop)
  - [ ] Maintain WiFi/MQTT with reconnect + LWT
  - [ ] Publish boot/version on connect and periodic health
- [ ] Centralize MQTT ownership in bootstrap (single client)
  - [ ] Implement message router and dispatch table for app-registered topics
  - [ ] Add wildcard/topic de-duplication logic
- [ ] Define and expose runtime API to app
  - [ ] `publish(topic, payload, retain=False)`
  - [ ] `subscribe(topic, callback, fast=False)` and `unsubscribe(topic)`
  - [ ] `sos(error, message="")`, `now_ms()`; optional `log()`
  - [ ] Enforce fast-callback budget and safety wrappers
- [ ] Keep OTA strictly in bootstrap
  - [ ] On update: publish `update_received` → `updating`
  - [ ] Quiesce app via `shutdown(reason="update")` with timeout
  - [ ] Apply update (protect bootstrap; temp-write then rename)
  - [ ] Publish `updated` then `machine.reset()`
  - [ ] Publish SOS on any error, remain responsive

#### MQTT Communication
- [ ] Set up MQTT broker on Linux server
  - [ ] Install and configure Mosquitto
  - [ ] Implement security settings and access control
  - [ ] Configure persistence and logging
  - [ ] Set up MQTT topic structure

- [ ] Implement basic MQTT client
  - [x] Create `mqtt_client.py` in shared directory
  - [ ] Implement device identity and authentication
  - [ ] Add health message publishing
  - [ ] Implement update command handling
  - [ ] Add last will and testament for offline detection
  - [ ] Add reconnection logic
  - [ ] Migrate device apps to use bootstrap-owned MQTT via runtime (no app-owned clients)

#### SOS Message System
- [ ] Implement SOS message generation
  - [ ] Create SOS message format and schema
  - [ ] Implement error detail collection
  - [ ] Add timestamp and device identification
  - [ ] Implement SOS message publishing
  - [ ] Centralize SOS publishing in bootstrap; expose `runtime.sos()` for apps

#### Development Dashboard
- [ ] Create basic web dashboard
  - [ ] Set up FastAPI server structure
  - [ ] Implement device status display
  - [ ] Add manual update triggering interface
  - [ ] Create SOS message viewer
  - [ ] Implement basic authentication

### Phase 2: Device Integration

#### Application Layer Separation
- [ ] Refactor existing device code
  - [ ] Move device-specific code to app/ directories
  - [ ] Implement clean separation between bootstrap and application
  - [ ] Create device configuration files
  - [ ] Standardize MQTT topic usage
  - [ ] Replace infinite-loop `main()` with plugin lifecycle
    - [ ] `init(runtime)` sets up hardware and subscriptions
    - [ ] `tick()` performs periodic work quickly
    - [ ] `shutdown(reason)` quiesces app for OTA/reset

- [ ] Implement device-specific functionality
  - [ ] Create City Power Monitor application
  - [ ] Create Freezer Monitor application
  - [ ] Create Garage Controller application
  - [ ] Implement sensor reading and control logic
  - [x] Create House Monitor application scaffold
  - [ ] Refactor Garage Controller to runtime plugin API (2025-09-07)

#### HTTP Update Testing
- [ ] Test update system
  - [ ] Verify selective download functionality
  - [ ] Test update deployment process
  - [ ] Validate file integrity after updates
  - [ ] Test update failure scenarios
  - [ ] Measure update performance and optimize
  - [x] Add OTA progress/status logging via MQTT (`update_received`, `updating`, `updated`; SOS on errors) (2025-09-07)
  - [ ] Validate app quiesce behavior with timeout during OTA (2025-09-07)
  - [ ] Verify post-update reset reloads updated shared/app modules

#### Error Handling Integration
- [ ] Implement comprehensive error handling
  - [ ] Add try-except blocks for all critical operations
  - [ ] Implement graceful degradation for sensor failures
  - [ ] Add detailed error reporting
  - [ ] Test SOS generation for various failure scenarios
  - [ ] Implement recovery workflows
  - [ ] Ensure app exceptions in `tick()`/callbacks do not crash bootstrap; SOS + continue

### Weather Time-Series Feature (2025-09-08)
- [x] Database: create time-series query to aggregate weather (temperature_f, pressure_inhg) by bucket
- [x] API: add `GET /api/garage/weather/history` with `start`, `end`, `range`, `bucket` params
- [x] Server deps: add `python-dateutil` for ISO parsing
- [x] MQTT ingestion: verify metric names align with DB query (`garage_temperature_f`, `garage_pressure_inhg`)
- [x] Android API: add `api.getWeatherHistory()` and `useWeatherHistory()` hook
- [x] Android UI: Weather graphs screen under `History` tab rendering temperature and pressure
- [x] Android Nav: Weather tile on `HomeScreen` navigates to `History` (Weather graphs)
- [ ] Future: add range selector (24h, 7d, 30d) and bucket control in UI
- [ ] Future: smoothing/rolling average and downsampling on server
- [ ] Future: paginate/stream large ranges via server-side bucketing only

### Phase 3: Production Deployment
{{ ... }}

## Testing Plan (2025-09-07)
- [ ] Command responsiveness: publish door/light commands → verify sub-10ms to tens of ms action
- [ ] OTA happy path: `update_received` → `updating` → `updated` → reset → boot/health
- [ ] OTA error path: induce HTTP error → SOS emitted; bootstrap remains responsive
- [ ] App fault: raise in `tick()` → SOS; device still accepts OTA
- [ ] Network drop: broker down/up → bootstrap reconnects; app resumes
- [ ] File write safety: temp-write + rename ensures no partials

## Discovered During Work

- [x] Add SOS when weather station (BMP388) has no reading, rate-limited to avoid spam (2025-09-08)
- [x] UI polish: Make garage door tile match flood light tile styling on HomeScreen (2025-09-08)
- [x] UI: Rearranged freezer monitors side-by-side and removed thresholds buttons on HomeScreen (2025-09-08)
- [x] Alerts: Expose structured current alerts via /api/alerts/current and consume in app SOS panel (2025-09-08)
- [x] Weather Time-Series Feature: Implemented database query, API endpoint, and Android UI for weather graphs (2025-09-08)
