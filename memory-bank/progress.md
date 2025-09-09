# Progress - IRIS

## What Works

### Infrastructure Components

#### Deployment System ✓

- `mpremote`-based deployment script successfully uploads code to devices
- Config merging combines network and device-specific settings
- File structure properly organized for bootstrap/app separation
- Soft reset triggers bootstrap initialization

#### Docker Stack ✓

- Docker Compose orchestrates all server services
- Mosquitto MQTT broker running with authentication
- PostgreSQL database with proper schema
- FastAPI server with REST endpoints
- Volume persistence for database and MQTT

#### Mobile App Foundation ✓

- React Native app with Expo framework
- Material Design UI with React Native Paper
- Tab navigation structure
- API client connecting to server
- React Query for state management

### Implemented Features

#### Server API Endpoints ✓

- `/api/garage/door` - Control and status
- `/api/garage/light` - Flood light control
- `/api/garage/weather/history` - Time-series data with bucketing
- `/api/alerts/current` - Structured alert data
- `/api/devices/{device_id}/update` - OTA trigger

#### Mobile App Screens ✓

- HomeScreen with status tiles
- Weather history graphs (temperature and pressure)
- SOS panel showing current alerts
- Settings screen structure
- Device management interface

#### Basic Device Code ✓

- Bootstrap files created and deployable
- Shared WiFi and MQTT modules
- Garage controller minimal app
- House monitor scaffold
- Config loading from JSON

## What's Left to Build

### Phase 1: Bootstrap Infrastructure (Current Priority)

#### Non-Blocking Scheduler ⏳

- [ ] Convert bootstrap main loop to 50-100 Hz scheduler
- [ ] Implement continuous MQTT message pumping
- [ ] Add WiFi/MQTT reconnection with backoff
- [ ] Publish periodic health heartbeats
- [ ] LED state indication

#### Runtime API ⏳

- [ ] Create runtime object for app interaction
- [ ] Implement publish/subscribe/unsubscribe methods
- [ ] Add SOS and logging methods
- [ ] Enforce callback timing budgets
- [ ] Message routing and dispatch

#### Application Lifecycle ⏳

- [ ] Replace infinite loop with init/tick/shutdown
- [ ] Implement cooperative multitasking
- [ ] Add timeout handling for shutdown
- [ ] Exception catching without bootstrap crash

#### OTA Update Flow ⏳

- [ ] Quiesce app before update
- [ ] Status progression publishing
- [ ] HTTP file download and verification
- [ ] Temp-write then rename strategy
- [ ] Post-update reset

### Phase 2: Device Integration

#### City Power Monitor 🔮

- [ ] Transformer input circuit design
- [ ] Power presence detection logic
- [ ] Heartbeat publishing
- [ ] Last Will for offline detection

#### Freezer Monitoring 🔮

- [ ] DS18B20 temperature sensor integration
- [ ] Reed switch door monitoring
- [ ] Ajar timing logic
- [ ] Alert threshold checking

#### Garage Controller Full Implementation 🔮

- [ ] Garage door relay control
- [ ] Position sensing with dual reed switches
- [ ] State machine for door movement
- [ ] BMP388 weather station integration
- [ ] Flood light relay control

### Phase 3: Production Features

#### Alert System 🔮

- [ ] Push notifications via FCM
- [ ] Email alerts for critical issues
- [ ] Alert acknowledgment workflow
- [ ] Historical alert tracking
- [ ] Alert severity levels

#### Advanced Features 🔮

- [ ] Historical data analysis
- [ ] Predictive maintenance
- [ ] Energy usage tracking
- [ ] Automation rules engine
- [ ] Voice control integration

## Current Status

### Development Environment

- **Repository**: Single monorepo structure established
- **Version Control**: Git with GitHub remote configured
- **IDE**: Windsurf AI editor in use
- **Testing**: Manual testing via MQTT monitoring

### Server Status

- **MQTT Broker**: Running on port 1883 with authentication
- **Database**: PostgreSQL with initial schema
- **API Server**: FastAPI on port 8000
- **Docker**: All services containerized
- **Monitoring**: Basic logging to stdout

### Device Status

- **Garage Controller**: Minimal blink app deployed
- **House Monitor**: Scaffold created, not deployed
- **City Power Monitor**: Planned, not started
- **Bootstrap**: Basic version deployed, needs scheduler

### Mobile App Status

- **Framework**: React Native with Expo configured
- **UI Components**: Basic screens implemented
- **API Integration**: Connected to local server
- **Charts**: Weather graphs working
- **Notifications**: Structure in place, not active

## Known Issues

### Critical Issues 🔴

1. **Bootstrap Not Cooperative**: Current bootstrap uses blocking loops
2. **No OTA Implementation**: Update system not functional
3. **App Owns MQTT**: Applications create their own clients
4. **No Error Recovery**: Exceptions crash the device

### Important Issues 🟡

1. **No Health Monitoring**: Devices don't publish health status
2. **Missing Sensors**: Hardware not connected or coded
3. **No Alert Delivery**: Push notifications not configured
4. **Limited Testing**: No automated test coverage

### Minor Issues 🟢

1. **UI Polish Needed**: Mobile app needs refinement
2. **Documentation Gaps**: Some features undocumented
3. **Performance Unoptimized**: No profiling done yet
4. **Logging Incomplete**: Need structured logging

## Evolution of Project Decisions

### Initial Approach (Abandoned)

- **Decision**: Apps own their execution and resources
- **Problem**: Apps could brick devices during updates
- **Learning**: Need separation of concerns

### Git-Based Updates (Abandoned)

- **Decision**: Use Git on devices for updates
- **Problem**: Too heavy for Pico W resources
- **Learning**: HTTP downloads are sufficient

### Current Architecture (Active)

- **Decision**: Immortal bootstrap with plugin apps
- **Benefits**: Always recoverable, clean updates
- **Status**: Implementation in progress

### Scheduler Design (In Progress)

- **Decision**: Non-blocking cooperative scheduler
- **Rationale**: Enables responsiveness and multitasking
- **Challenge**: Balancing timing requirements

### Runtime API (Planned)

- **Decision**: Bootstrap provides all system access
- **Rationale**: Single point of control
- **Status**: Design complete, implementation pending

## Metrics & Measurements

### Current Performance

- **MQTT Latency**: ~50ms local network
- **API Response**: ~100ms for queries
- **Deploy Time**: ~30 seconds per device
- **Docker Startup**: ~15 seconds all services

### Target Performance

- **Command Response**: < 100ms end-to-end
- **Health Interval**: Every 30 seconds
- **OTA Duration**: < 5 minutes
- **Alert Delivery**: < 60 seconds

### Resource Usage

- **Pico W RAM**: ~100KB used (of 264KB)
- **Pico W Flash**: ~500KB used (of 2MB)
- **Server RAM**: ~500MB all services
- **Database Size**: < 100MB currently

## Risk Assessment

### High Risk

1. **Bootstrap Bugs**: Could brick all devices
2. **Network Dependency**: No offline operation
3. **Single Server**: No redundancy

### Medium Risk

1. **OTA Failures**: Devices need manual recovery
2. **Database Growth**: No data retention policy
3. **Security**: Basic authentication only

### Low Risk

1. **Performance**: Adequate for home use
2. **Scalability**: Can handle 10+ devices
3. **Maintenance**: Code is well-organized

## Next Sprint Focus

### Week 1 Priority

1. Implement non-blocking scheduler in bootstrap
2. Create runtime API facade
3. Convert garage-controller to plugin architecture
4. Test command responsiveness

### Week 2 Priority

1. Implement OTA update flow
2. Add health monitoring
3. Test update scenarios
4. Document findings

### Week 3 Priority

1. Implement actual sensors
2. Add garage door control
3. Test hardware integration
4. Deploy to production devices

## Success Indicators

### Completed ✅

- Project structure established
- Development environment configured
- Basic deployment working
- Server stack operational
- Mobile app foundation built

### In Progress 🔄

- Bootstrap scheduler implementation
- Runtime API development
- Application lifecycle management
- OTA update system

### Blocked ❌

- Hardware sensor integration (waiting for scheduler)
- Alert delivery (waiting for device implementation)
- Production deployment (waiting for Phase 1)
- Advanced features (waiting for basics)

## Lessons Learned

### What Worked Well

1. **Docker Compose**: Simplified server management
2. **Single Repository**: Easy coordination
3. **Config Merging**: Flexible deployment
4. **React Native**: Rapid UI development

### What Didn't Work

1. **Blocking Architecture**: Not responsive enough
2. **App-Owned Resources**: Update conflicts
3. **Complex OTA**: Overengineered initially

### Key Insights

1. **Simplicity Wins**: Start minimal, add complexity later
2. **Separation Critical**: Bootstrap must be isolated
3. **Testing Essential**: Manual testing is insufficient
4. **Documentation Helps**: Clear specs prevent rework
