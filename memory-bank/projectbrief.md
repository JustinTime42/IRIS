# Project Brief - IRIS (Intelligent Residence Information System)

## Project Identity

**Name**: IRIS - Intelligent Residence Information System  
**Repository**: corvids-nest (on disk) / IRIS (on GitHub)  
**Type**: Home Automation System  
**Architecture**: Distributed microcontroller network with centralized server

## Core Requirements

### Primary Goals

1. **Bulletproof Reliability**: Immortal bootstrap layer that can always recover from application failures
2. **Remote Management**: Over-the-air updates via HTTP without physical access
3. **Home Monitoring**: Track critical home systems (power, freezers, garage)
4. **Smart Control**: Automated and manual control of garage door and outdoor lighting
5. **Alert System**: Proactive notifications for issues requiring human intervention

### System Objectives

- Unbreakable recovery through separation of bootstrap from application logic
- Single source of truth via unified repository structure
- Human-in-the-loop error handling via SOS messaging
- HTTP-based updates using GitHub API (no Git dependencies on devices)
- VPN-based remote access with no exposed ports

## Hardware Scope

### Pico W #1 - House Monitor

- Monitor city power presence (transformer input detection)
- Monitor chest freezer temperature (DS18B20 sensor)
- Detect freezer door ajar status (reed switch with timing)
- Generator-backed power source

### Pico W #2 - Garage Controller

- Control garage door (relay) with position monitoring (dual reed switches)
- Control outdoor flood lights (relay)
- Weather station (BMP388 for temperature and pressure)
- Monitor garage chest freezer temperature (DS18B20)
- Generator-backed power source

### Linux Server

- MQTT broker for all device communication
- PostgreSQL database for data persistence
- FastAPI server for REST endpoints and WebSocket
- Alert engine for notifications
- Device health monitoring and coordination

## Software Architecture

### Two-Tier Device Architecture

1. **Bootstrap Layer** (Immortal, never updated)

   - WiFi and MQTT connection management
   - Non-blocking scheduler loop
   - OTA update orchestration
   - Application lifecycle supervision
   - SOS message transmission

2. **Application Layer** (Updated via OTA)
   - Device-specific business logic
   - Sensor reading and control
   - MQTT topic subscriptions
   - Telemetry publishing

### Communication Protocol

- MQTT hub-and-spoke architecture
- Structured topic hierarchy under `home/`
- JSON payloads for complex data
- Last Will and Testament for offline detection

## Success Criteria

- Devices remain responsive even during application failures
- OTA updates complete without manual intervention
- Critical alerts reach users within 60 seconds
- System recovers automatically from network disruptions
- All device health visible from mobile app

## Constraints

- Windows 11 development environment
- MicroPython for Pico W devices
- React Native for mobile app
- Single repository structure
- Generator-backed power for critical components
