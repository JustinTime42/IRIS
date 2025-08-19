IRIS - Intelligent Residence Information System
Software Design Specification
======================================================

## Executive Summary

--------------------

This document outlines the software architecture for a comprehensive home automation system designed around distributed Pico W microcontrollers with bulletproof bootstrap architecture, centralized Linux server coordination, and modern mobile interfaces. The system prioritizes reliability through separation of critical boot functions from application logic, uses HTTP-based over-the-air updates, and employs a single repository structure for streamlined development and deployment.

## System Overview

------------------

### 2.1 Core Objectives

* **Unbreakable Recovery**: Immortal bootstrap layer that can always recover from application failures
* **Single Source of Truth**: Unified repository containing all system components for coordinated development
* **Human-in-the-Loop Error Handling**: Intelligent SOS messaging when intervention is needed
* **HTTP-Based Updates**: Reliable, simple updates using GitHub API without Git dependencies
* **Maintainability**: Clear separation between bulletproof system functions and application logic
* **Security**: VPN-based remote access, no exposed ports, encrypted communications

### 2.2 High-Level Architecture

The system employs a hub-and-spoke MQTT architecture with the Linux server as the central coordinator. Each Pico W operates with a two-tier architecture: an immortal bootstrap layer that handles system functions (updates, error recovery, MQTT communication) and a replaceable application layer that handles device-specific functionality. All components live in a single repository with HTTP-based selective deployment.

## System Components

--------------------

### 3.1 Hardware Components

#### 3.1.1 Pico W #1 - House Monitor

* **Location**: Upright freezer area
* **Power Source**: Generator-backed circuit
* **Primary Functions**:
  * City power presence detection via MW RS-25-5 transformer input
  * Chest freezer temperature monitoring (single DS18B20)
  * Reed switch door ajar detection with timing

#### 3.1.2 Pico W #2 - Garage Controller

* **Location**: Garage
* **Power Source**: Generator-backed circuit
* **Primary Functions**:
  * Garage door control (relay) and position monitoring (dual reed switches)
  * Outdoor flood light control (relay)
  * Weather station (BMP388 sensor for temperature, pressure)
  * Chest freezer temperature monitoring (single DS18B20)

#### 3.1.3 Linux Server

* **Hardware**: Existing computer
* **Power Source**: Generator-backed circuit
* **Primary Functions**: MQTT broker, database, API server, alert coordination

### 3.2 Software Architecture

#### 3.2.1 Pico W Two-Tier Architecture

**Tier 1: Immortal Bootstrap Layer** (Never Updated)
* **Runtime**: MicroPython with minimal, bulletproof code
* **Responsibilities**: 
  * WiFi and MQTT connection management
  * HTTP-based update downloads and deployment
  * Application error handling and recovery
  * SOS message transmission
  * Device identification and health monitoring
* **Files**: `main.py`, `bootstrap_manager.py` (flashed once, never changed)

**Tier 2: Application Layer** (Updated via OTA)
* **Runtime**: MicroPython application code
* **Responsibilities**:
  * Device-specific sensor reading and control
  * MQTT data publishing and command handling
  * Business logic for automation functions
* **Files**: All files in `app/` directory (replaced during updates)

#### 3.2.2 Repository Structure

Note: The project name is IRIS (Intelligent Residence Information System). The repository folder on disk may still be named `corvids-nest`.

```
corvids-nest/
├── android/                    # React Native app (future)
├── devices/
│   ├── bootstrap/              # Immortal bootstrap (never OTA-updated)
│   │   ├── main.py
│   │   ├── bootstrap_manager.py
│   │   └── http_updater.py
│   └── <device_id>/
│       └── app/                # Device-specific app sources (deployed to :/app)
│           ├── main.py         # Entrypoint, defines main()
│           └── ...             # Optional helpers for that device
├── shared/                     # Reusable MicroPython modules
│   ├── __init__.py
│   ├── wifi_manager.py
│   ├── mqtt_client.py
│   └── config_manager.py
│       └── config/
├── shared/
│   ├── mqtt_client.py          # Common MQTT functionality
│   ├── wifi_manager.py         # WiFi connection management
│   ├── sensor_utils.py         # Common sensor utilities
│   └── config_manager.py       # Configuration management
└── deployment/
    ├── device_configs.json     # Device identification mapping
    └── scripts/                # Deployment automation
```

#### 3.2.3 Linux Server Stack

* **MQTT Broker**: Mosquitto for device communication
* **Database**: PostgreSQL for all data storage (historical, configuration, system events)
* **API Server**: FastAPI providing REST endpoints and WebSocket support
* **Alert Engine**: Monitors sensor thresholds, device health, and SOS messages; sends FCM notifications
* **Device Monitor**: Tracks device health and coordinates recovery operations
* **Background Services**: Data logging, alert processing, system health monitoring
* **In-Memory Cache**: Python dictionaries for current sensor values and device status

#### 3.2.4 Client Applications

* **React Native Mobile App**: Full-featured control and monitoring interface built with Expo and React Native Paper for Material Design UI components. Includes FCM push notifications and comprehensive SOS incident management
* **Android Widget**: Quick status display and common actions (Kotlin-based)
* **Development Web Dashboard**: Local development tool for testing and manual device updates
* **Future LLM Integration**: Voice command processing via MCP servers

## Communication Architecture

-----------------------------

### 4.1 MQTT Topic Structure

    home/
    ├── garage/
    │   ├── door/
    │   │   ├── status → "closed", "open", "opening", "closing"
    │   │   └── command → "open", "close"
    │   ├── light/
    │   │   ├── status → "on", "off"
    │   │   └── command → "on", "off", "toggle"
    │   ├── weather/
    │   │   ├── temperature → float (°F)
    │   │   ├── humidity → float (%)
    │   │   └── pressure → float (inHg)
    │   └── freezer/
    │       └── temperature → float (°F)
    ├── power/
    │   └── city/
    │       ├── status → "online", "offline" (via last will)
    │       └── heartbeat → timestamp
    ├── freezer/
    │   ├── temperature/
    │   │   ├── main → float (°F)
    │   │   └── backup → float (°F)
    │   └── door/
    │       ├── status → "closed", "open"
    │       └── ajar_time → int (seconds)
    └── system/
        └── {device_id}/
            ├── update → "update" (triggers HTTP download)
            ├── status → "running", "updating", "sos", "recovered"
            ├── sos → JSON: {"error": "...", "timestamp": int, "details": "..."}
            ├── health → "online", "error", "needs_help"
            └── version → commit_sha or "unknown"

### 4.2 Bootstrap Layer Communication

The immortal bootstrap layer handles all critical MQTT communication:

```python
# Bootstrap MQTT Topics (Device → Server)
home/system/{device_id}/sos         # Emergency help requests
home/system/{device_id}/status      # System status updates  
home/system/{device_id}/health      # Periodic health checks
home/system/{device_id}/boot        # Boot notifications

# Bootstrap MQTT Topics (Server → Device)  
home/system/{device_id}/update      # Trigger OTA updates
home/system/{device_id}/reboot      # Force device reboot
home/system/{device_id}/ping        # Health check requests
```

### 4.3 API Architecture

#### 4.3.1 REST Endpoints

* **Commands**: POST endpoints for device control operations
* **Status**: GET endpoints for current system state
* **History**: GET endpoints for historical data with pagination  
* **Updates**: POST endpoints for triggering device updates
* **SOS Management**: GET/POST endpoints for viewing and resolving SOS incidents
* **Configuration**: GET/POST endpoints for system configuration

#### 4.3.2 WebSocket Channels

* **Real-time Status**: Live updates for all sensor data and device states
* **SOS Alerts**: Immediate notification of device distress signals
* **Update Progress**: Live feedback during device update operations
* **System Health**: Device health status and recovery operations
* **Connection Health**: Heartbeat and connection status for all devices

### 4.4 Remote Access Strategy

* **Primary**: Tailscale VPN for secure remote access
* **Architecture**: All remote connections appear as local network access
* **Security**: No port forwarding, no exposed services, encrypted mesh network
* **Fallback**: Prepared for reverse proxy implementation if needed

## Bootstrap Layer Architecture

----------------------------------

### 5.1 Immortal Bootstrap Design

The bootstrap layer is designed to be completely reliable and never require updates. It contains a hardcoded device ID and minimal, bulletproof code responsible for WiFi connection, MQTT communication, and application lifecycle management. The bootstrap never attempts to update itself, ensuring it remains a stable recovery mechanism.

### 5.2 Bootstrap Manager Functions

The bootstrap manager implements the core system loop that never exits. It establishes network connectivity, subscribes to MQTT update commands, and attempts to load and run the application layer. When the application crashes or fails, the bootstrap catches all exceptions and handles them gracefully without terminating the system process.

Key responsibilities include:
* **Application Lifecycle Management**: Loading, running, and restarting the application layer
* **Error Recovery**: Catching application failures and maintaining system stability
* **SOS Communication**: Sending detailed error information to the server when help is needed
* **Update Coordination**: Receiving and executing OTA update commands
* **Help Mode**: Entering a responsive waiting state when manual intervention is required

### 5.3 HTTP Update System

The HTTP updater uses GitHub's REST API to selectively download only the files needed by the specific device. It downloads device-specific application code, shared libraries, and configuration files while never touching the bootstrap layer. The update process overwrites existing application files and reports success or failure status back to the server via MQTT.

## Data Management and Alert System

----------------------------------

### 5.1 Enhanced Alert System

The alert system now includes device health monitoring and SOS handling:

#### 5.1.1 Alert Types

* **Environmental Alerts**: Freezer temperature, door ajar conditions
* **Device Health Alerts**: Device offline, repeated failures, communication issues
* **SOS Alerts**: Device distress signals requiring immediate attention
* **System Alerts**: Power outages, infrastructure failures

#### 5.1.2 SOS Message Handling

The SOS handler processes incoming distress signals from devices and coordinates the human intervention workflow. When a device sends an SOS message, the system immediately logs the incident, tracks the device as needing help, and sends high-priority push notifications to the mobile application.

The SOS system maintains state for all active incidents and provides detailed error information including device identification, error descriptions, timestamps, and system state at the time of failure. This enables quick diagnosis and targeted fixes rather than blind troubleshooting.

### 5.2 Data Storage Strategy

* **Real-time Data**: In-memory Python dictionaries for current sensor values and device status
* **Historical Data**: PostgreSQL with time-series tables for sensor readings and system events
* **SOS Incidents**: PostgreSQL table with full SOS history and resolution tracking
* **Device Health**: PostgreSQL tables tracking device status, boot cycles, and error patterns
* **Configuration**: PostgreSQL tables with in-memory caching for device configurations

### 5.3 Database Schema Design

The database schema includes specialized tables for tracking SOS incidents, device health metrics, and boot cycles. The SOS incidents table maintains a complete audit trail of all device failures, resolution status, and human intervention notes. 

Device health tracking includes real-time status, boot counts, error counts, last known errors, and version information. The boot log captures all device startup events with contextual information about boot reasons and success status.

Key schema components:
* **SOS Incidents**: Complete incident tracking with resolution workflow
* **Device Health**: Real-time status and historical health metrics  
* **Device Boots**: Audit trail of all device startup events
* **System Events**: Comprehensive logging of power outages and system changes

## Update and Deployment Strategy

---------------------------------

### 6.1 Single Repository Workflow

**Development Process**:
1. **Make changes** to any component (Android, server, or device code)
2. **Commit to repository** - all components stay synchronized
3. **Trigger updates** via mobile app or web dashboard
4. **Devices update** via HTTP API selective download

### 6.2 HTTP-Based Update System

**Update Trigger Flow**:
```
Mobile App → Server API → MQTT Command → Device Bootstrap → GitHub API → Deploy
```

**Device Update Process**:
1. **Bootstrap receives** MQTT update command
2. **Downloads files** via GitHub API (only device-specific directories)
3. **Overwrites application** files (never touches bootstrap)
4. **Reports status** via MQTT
5. **Attempts to run** new application code
6. **Sends SOS** if new code fails

### 6.3 Update Safety Mechanisms

* **Bootstrap Isolation**: Update mechanism never gets updated, eliminating bootstrap corruption
* **Selective Download**: Only application code gets replaced
* **Immediate Feedback**: SOS messages provide instant failure notification
* **Human Oversight**: No automatic retries, requires human intervention for recovery
* **GitHub as Backup**: Source repository serves as the ultimate backup system

### 6.5 Deployment Automation

The repository includes `deployment/scripts/deploy.py`, a Python script that automates flashing and configuration of Pico W devices using `mpremote`:

* **Device selection**: Reads `deployment/device_index.json` and prompts the operator to choose a device entry (which specifies the per-device config path).
* **Port selection**: Lists available Pico serial ports via `mpremote connect list` and prompts for confirmation.
* **Config merge**: Merges `deployment/common/network.json` (shared WiFi/MQTT) with the selected per-device `device.json`. Device-specific values override common values. The merged output is uploaded as `:/config/device.json`.
* **File deployment**:
  - Uploads `devices/bootstrap/*` into device root (`:/main.py`, `:/bootstrap_manager.py`, `:/http_updater.py`).
  - Uploads the entire `shared/` directory to `:/shared/`.
  - If present, uploads `devices/<device_id>/app/` to `:/app/` (bootstrap imports `app.main.main()`).
* **Reset**: Soft-resets the device to start the bootstrap and app.

Security note: Per-device configs (with secrets) live under `deployment/devices/<device_id>/device.json` and are gitignored by default, while the template `_template.device.json` remains tracked.

### 6.4 Development and Testing Workflow

The development workflow leverages the single repository structure for coordinated updates across all system components. Developers can make changes to any component, commit to the repository, and trigger selective updates to test devices. The workflow supports both individual device testing and coordinated system-wide deployments.

Key workflow elements:
1. **Local Development**: Edit code with immediate testing via development dashboard
2. **Version Control**: Single repository maintains all component synchronization  
3. **Selective Testing**: Deploy updates to individual devices for validation
4. **Coordinated Deployment**: Update multiple devices simultaneously
5. **SOS Monitoring**: Track deployment success via SOS message absence

## Error Handling and Reliability

---------------------------------

### 7.1 Multi-Layer Error Handling

**Layer 1: Bootstrap (Bulletproof)**
* Handles all system-level failures
* WiFi/MQTT reconnection
* Application crash recovery
* SOS message transmission
* Never gets updated

**Layer 2: Application (Replaceable)**
* Device-specific error handling
* Graceful sensor failure handling
* MQTT communication errors
* Updated via OTA as needed

### 7.2 Failure Recovery Patterns

**Application Crashes**:
```
App Exception → Bootstrap Catches → SOS Message → Human Fixes → Update Command → Recovery
```

**Boot Failures**:
```
Boot Failure → Bootstrap Detects → SOS Message → Wait for Fix → Update Command → Retry
```

**Update Failures**:
```
Update Exception → Bootstrap Catches → SOS Message → Human Investigates → Fixed Update
```

### 7.3 Device Health Monitoring

The device health monitoring system continuously tracks all devices for signs of failure or degradation. It monitors heartbeat messages, tracks SOS frequency patterns, and detects boot loop conditions that indicate persistent problems.

The monitoring system implements escalation procedures for devices showing repeated failures and provides early warning for devices that may need intervention. Health metrics include connectivity status, error frequency, boot success rates, and response time patterns.

## Security Architecture

------------------------

### 8.1 Network Security

* **VPN Access**: Tailscale mesh network for all remote access
* **Internal Communication**: MQTT over local network only
* **No External Exposure**: No services exposed to public internet
* **GitHub API**: Uses personal access tokens for repository access

### 8.2 Application Security

* **API Authentication**: JWT tokens for client application access
* **Input Validation**: Comprehensive validation of all API inputs and MQTT messages
* **Rate Limiting**: Protection against abuse and DoS attacks
* **SOS Validation**: Verification of SOS message authenticity and rate limiting

## Implementation Phases

-------------------------

### 12.1 Phase 1: Bootstrap Infrastructure

* **Bootstrap layer development**: Immortal bootstrap code with HTTP updater
* **Basic MQTT communication**: Device identity, health messages, update commands
* **GitHub API integration**: Selective file download system
* **SOS message system**: Basic error reporting and mobile notifications
* **Development dashboard**: Manual update triggering and device monitoring

### 12.2 Phase 2: Device Integration

* **Application layer separation**: Move existing device code to app/ directories
* **HTTP update testing**: Verify selective download and deployment
* **Error handling integration**: Test SOS generation and recovery workflows
* **Mobile SOS handling**: FCM integration and SOS incident management
* **Multi-device coordination**: Update multiple devices simultaneously

### 12.3 Phase 3: Production Deployment

* **Physical device setup**: Flash bootstrap code to all devices
* **Application deployment**: Initial OTA deployment of device applications
* **Mobile app completion**: Full SOS handling and device management features
* **System monitoring**: Comprehensive device health monitoring and alerting

### 12.4 Phase 4: Advanced Features

* **Historical SOS analysis**: Pattern recognition and predictive maintenance
* **Automated diagnostics**: Enhanced error reporting with system state
* **LLM integration**: Voice command processing and intelligent error analysis
* **Performance optimization**: System refinement based on operational data

## Mobile Application Integration

----------------------------------

### 13.1 React Native Architecture

The mobile application is built using React Native with Expo for streamlined development and deployment. The UI implements Material Design principles through React Native Paper components, providing a consistent and intuitive user experience.

**Technology Stack**:
* **React Native**: Cross-platform mobile development framework
* **Expo**: Development platform with simplified build and deployment
* **React Native Paper**: Material Design component library
* **Firebase Cloud Messaging**: Push notification delivery
* **WebSocket Integration**: Real-time status updates and system monitoring

### 13.2 SOS Handling

The mobile application provides comprehensive SOS incident management:

* **Real-time SOS notifications**: High-priority FCM messages for immediate attention
* **SOS dashboard**: Current and historical SOS incidents with status tracking
* **Quick recovery actions**: One-tap update triggering for affected devices
* **Diagnostic information**: Detailed error logs and device state information
* **Resolution tracking**: Mark incidents as resolved with notes

### 13.3 Device Management

* **Device status overview**: Real-time health status for all devices
* **Manual update triggering**: Force updates to individual or multiple devices
* **Update history**: Track successful and failed update attempts
* **Device configuration**: Remote configuration management via MQTT

This updated software design specification provides the architectural foundation for building a robust, maintainable home automation system with bulletproof error recovery, unified repository management, and intelligent failure handling that minimizes the need for physical device access.