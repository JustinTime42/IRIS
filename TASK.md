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

#### SOS Message System
- [ ] Implement SOS message generation
  - [ ] Create SOS message format and schema
  - [ ] Implement error detail collection
  - [ ] Add timestamp and device identification
  - [ ] Implement SOS message publishing

- [ ] Implement SOS handling on server
  - [ ] Create SOS message listener
  - [ ] Implement database storage for SOS incidents
  - [ ] Add notification system for SOS messages
  - [ ] Implement SOS resolution tracking

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

- [ ] Implement device-specific functionality
  - [ ] Create City Power Monitor application
  - [ ] Create Freezer Monitor application
  - [ ] Create Garage Controller application
  - [ ] Implement sensor reading and control logic
  - [x] Create House Monitor application scaffold

#### HTTP Update Testing
- [ ] Test update system
  - [ ] Verify selective download functionality
  - [ ] Test update deployment process
  - [ ] Validate file integrity after updates
  - [ ] Test update failure scenarios
  - [ ] Measure update performance and optimize

#### Error Handling Integration
- [ ] Implement comprehensive error handling
  - [ ] Add try-except blocks for all critical operations
  - [ ] Implement graceful degradation for sensor failures
  - [ ] Add detailed error reporting
  - [ ] Test SOS generation for various failure scenarios
  - [ ] Implement recovery workflows

#### Mobile App Development
- [ ] Set up React Native project
  - [ ] Initialize Expo project
  - [ ] Configure React Native Paper
  - [ ] Set up project structure
  - [ ] Configure development environment

- [ ] Implement core mobile functionality
  - [ ] Create device status display
  - [ ] Implement control interfaces
  - [ ] Add SOS notification handling
  - [ ] Implement update triggering
  - [ ] Add authentication and security

- [ ] Implement FCM integration
  - [ ] Set up Firebase project
  - [ ] Configure FCM for push notifications
  - [ ] Implement notification handling
  - [ ] Add high-priority alerts for SOS messages

#### Multi-Device Coordination
- [ ] Implement device coordination
  - [ ] Create device registry
  - [ ] Implement group update functionality
  - [ ] Add device dependency tracking
  - [ ] Create update sequencing logic

### Phase 3: Production Deployment

#### Physical Device Setup
- [ ] Prepare physical devices
  - [ ] Assemble hardware components
  - [ ] Flash bootstrap code to all Pico W devices
  - [ ] Configure device-specific settings
  - [ ] Test basic connectivity

- [ ] Install sensors and actuators
  - [ ] Install temperature sensors
  - [ ] Set up reed switches
  - [ ] Configure relays
  - [ ] Install weather station components

#### Application Deployment
- [ ] Deploy initial applications
  - [ ] Perform OTA deployment to all devices
  - [ ] Verify application functionality
  - [ ] Test sensor readings and control operations
  - [ ] Validate MQTT communication

#### Mobile App Completion
- [ ] Complete mobile application
  - [ ] Finalize UI/UX design
  - [ ] Implement all device control features
  - [ ] Add comprehensive SOS handling
  - [ ] Implement device management features
  - [ ] Add user preferences and settings

#### System Monitoring
- [ ] Implement comprehensive monitoring
  - [ ] Create device health dashboard
  - [ ] Implement alert thresholds
  - [ ] Add historical data visualization
  - [ ] Create system status overview
  - [ ] Implement notification preferences

### Phase 4: Advanced Features

#### Historical SOS Analysis
- [ ] Implement SOS analytics
  - [ ] Create SOS history database
  - [ ] Implement pattern recognition
  - [ ] Add failure trend analysis
  - [ ] Create predictive maintenance alerts

#### Automated Diagnostics
- [ ] Enhance error reporting
  - [ ] Add system state capture
  - [ ] Implement diagnostic routines
  - [ ] Create self-test functionality
  - [ ] Add detailed error classification

#### LLM Integration
- [ ] Implement voice command processing
  - [ ] Set up LLM integration
  - [ ] Create voice command parser
  - [ ] Implement natural language control
  - [ ] Add intelligent error analysis

#### Performance Optimization
- [ ] Optimize system performance
  - [ ] Analyze operational data
  - [ ] Identify bottlenecks
  - [ ] Implement performance improvements
  - [ ] Optimize power consumption
  - [ ] Reduce network overhead

---

## Server Components

### Database Setup
- [ ] Set up PostgreSQL database
  - [ ] Create database schema
  - [ ] Implement time-series tables
  - [ ] Set up SOS incident tracking
  - [ ] Create device health tables
  - [ ] Configure backup and recovery

### API Development
- [ ] Implement REST API
  - [ ] Create device control endpoints
  - [ ] Implement status query endpoints
  - [ ] Add historical data access
  - [ ] Implement update management
  - [ ] Create SOS management endpoints

- [ ] Implement WebSocket channels
  - [ ] Create real-time status updates
  - [ ] Implement SOS alert notifications
  - [ ] Add update progress tracking
  - [ ] Create system health monitoring

### Alert System
- [ ] Implement alert engine
  - [ ] Create alert types and priorities
  - [ ] Implement threshold monitoring
  - [ ] Add alert notification system
  - [ ] Create alert history and tracking

### Remote Access
- [ ] Configure Tailscale VPN
  - [ ] Set up secure remote access
  - [ ] Configure device authentication
  - [ ] Implement access controls
  - [ ] Test remote functionality

---

## Device-Specific Tasks

### City Power Monitor
- [ ] Implement power detection
  - [ ] Configure power source connection
  - [ ] Implement online status reporting
  - [ ] Add heartbeat mechanism
  - [ ] Create power outage detection

### Freezer Monitor
- [ ] Implement temperature monitoring
  - [ ] Configure DS18B20 sensor
  - [ ] Implement temperature reading
  - [ ] Add threshold alerts
  - [ ] Create temperature history logging

- [ ] Implement door monitoring
  - [ ] Configure reed switch
  - [ ] Implement door status detection
  - [ ] Add door ajar timing
  - [ ] Create door alert system

### Garage Controller
- [ ] Implement garage door control
  - [ ] Configure relay for door control
  - [ ] Set up reed switches for position detection
  - [ ] Implement open/close commands
  - [ ] Add position status reporting

- [ ] Implement light control
  - [ ] Configure relay for flood light
  - [ ] Implement on/off commands
  - [ ] Add status reporting

- [ ] Implement weather station
  - [ ] Configure BMP388 sensor
  - [ ] Implement temperature reading
  - [ ] Add humidity measurement
  - [ ] Implement pressure reading
  - [ ] Create weather data reporting

#### Progress Notes
- [x] Ported BMP388 driver to Pico W compatible MicroPython (`shared/vendor/bmp3xx.py`), removed micro:bit deps, initialized I2C on GP6/GP7, replaced sleeps, and updated read/write calls (2025-08-19)
- [ ] Verify on-device readings via deploy and import check; wire default I2C address 0x76 per SDO to GND (in progress)

- [ ] Implement freezer monitoring
  - [ ] Configure DS18B20 sensor
  - [ ] Implement temperature reading
  - [ ] Add threshold alerts
  - [ ] Create temperature history logging

---

## Backlog

### Future Enhancements
- [ ] Implement energy monitoring
  - [ ] Add power consumption tracking
  - [ ] Create energy usage reports
  - [ ] Implement energy-saving features

- [ ] Add security features
  - [ ] Implement motion detection
  - [ ] Add camera integration
  - [ ] Create security alerts
  - [ ] Implement access logging

### User Experience
- [ ] Enhance mobile app
  - [ ] Add customizable dashboards
  - [ ] Implement themes and appearance options
  - [ ] Create widgets for quick access
  - [ ] Add advanced visualization

- [ ] Improve notification system
  - [ ] Add notification categories
  - [ ] Implement quiet hours
  - [ ] Create priority-based notifications
  - [ ] Add notification history

---

## Completed Tasks
- None yet

## Discovered During Work
- [x] Harden deployment script mpremote interactions with reset + retries to mitigate "could not enter raw repl" errors (2025-08-15)
- [x] Added scaffold for `devices/house-monitor/app/` with `main.py` and `sensors.py`; created `deployment/devices/house-monitor/README.md` to instruct creating local `device.json` (gitignored) (2025-08-15)
- [x] Renamed project branding to IRIS (Intelligent Residence Information System); updated `design_doc.md` and `README.md` accordingly (2025-08-15)
- [x] Deploy script: Added fallback to upload local `shared/vendor/bmp3xx.py` to device `/lib/` when `mip install bmp3xx` is unavailable (2025-08-18)
- [x] BMP388 driver uses I2C address 0x76 by default since SDO is tied to GND; Pico W I2C bus 1 on GP6 (SDA) / GP7 (SCL) at 400kHz (2025-08-19)

## Discovered Tasks & Notes
- [ ] Consider adding backup power monitoring for critical devices
- [ ] Evaluate additional sensor types for environmental monitoring
- [ ] Research low-power optimization for battery-operated devices
- [ ] Consider adding local caching for offline operation
- [ ] Evaluate mesh networking for improved reliability
