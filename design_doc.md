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
* **Runtime**: MicroPython with a minimal, bulletproof scheduler loop
* **Responsibilities**:
  * WiFi and MQTT connection management (single client owned by bootstrap)
  * Non-blocking main loop that never yields control to the app indefinitely
  * MQTT message pump and routing to app callbacks
  * HTTP-based OTA update orchestration (quiesce app → apply → reset)
  * Application lifecycle supervision (init/tick/shutdown)
  * SOS message transmission and health heartbeat
  * Device identification, boot/version announcements, LED indications
* **Files**: `devices/bootstrap/main.py`, `devices/bootstrap/bootstrap_manager.py`, `devices/bootstrap/http_updater.py` (flashed once, never changed)

**Tier 2: Application Layer** (Updated via OTA)
* **Runtime**: MicroPython application code as a cooperative plugin
* **Responsibilities**:
  * Device-specific IO and business logic
  * Register MQTT topic subscriptions via runtime and handle commands
  * Periodic telemetry and sensor publishing in short `tick()` slices
  * Quiesce quickly on `shutdown()` when the bootstrap initiates OTA
* **Files**: `devices/<device_id>/app/**` (replaced during updates)

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

```
home/
  garage/
    door/
      status → "closed", "open", "opening", "closing"
      command → "open", "close", "toggle"
    light/
      status → "on", "off"
      command → "on", "off", "toggle"
    weather/
      temperature → float (°F)
      humidity → float (%)
      pressure → float (inHg)
    freezer/
      temperature → float (°F)
  power/
    city/
      status → "online", "offline" (via last will)
      heartbeat → timestamp
  freezer/
    temperature/
      main → float (°F)
      backup → float (°F)
    door/
      status → "closed", "open"
      ajar_time → int (seconds)
  system/
    {device_id}/
      update → JSON manifest (triggers OTA)
      status → "running", "update_received", "updating", "updated", "alive"
      sos → JSON {error, message, timestamp, device_id}
      health → "online", "error", "needs_help"
      version → commit_sha or "unknown"
```

### 4.2 Bootstrap Layer Communication and Ownership

- Single MQTT client owned by the bootstrap for all topics.
- Bootstrap subscribes to system topics and any app-registered topics; dispatches app topics to registered callbacks.
- App publishes via the runtime provided by the bootstrap (no separate client in the app).

### 4.3 App Runtime Interface

The bootstrap passes a `runtime` object to the app during `init(runtime)`. The app never creates its own MQTT client.

```text
runtime.publish(topic: str, payload: str|bytes, retain: bool = False) -> bool
runtime.subscribe(topic: str, callback: Callable[[str, bytes], None], fast: bool = False) -> None
runtime.unsubscribe(topic: str) -> None
runtime.sos(error: str, message: str = "") -> None
runtime.now_ms() -> int
runtime.log(level: str, msg: str) -> None  # optional convenience
```

- fast=True runs the callback immediately in the dispatch path (must be short-running). Use for door/light commands.
- fast=False enqueues for processing in the next `tick()` to avoid long work in the dispatch path.

### 4.4 Bootstrap Scheduler Loop

- Frequency target: 50–100 Hz (10–20ms per iteration typical on Pico W).
- Each iteration:
  1) Update LED based on state
  2) Ensure WiFi connected (backoff)
  3) Ensure MQTT connected; publish LWT and boot/version on connect
  4) Pump MQTT messages and dispatch to system/app handlers
  5) Publish periodic health (e.g., every 30s)
  6) Call `app.tick()` if app is initialized (must return quickly)

- Error handling: any exception from app callbacks or `tick()` results in an SOS; bootstrap continues running and remains responsive to updates.

### 4.5 OTA Flow (Bootstrap-Only)

- Trigger: server publishes manifest to `home/system/{device_id}/update`.
- Bootstrap sequence:
  1) Publish `status=update_received`
  2) Publish `status=updating`
  3) Quiesce the app: call `app.shutdown(reason="update")` with a short timeout (e.g., 1–2s)
  4) Download and apply files via `HttpUpdater` (protect bootstrap files)
  5) Publish `status=updated`
  6) `machine.reset()` to reload updated modules cleanly
- On any failure during OTA: publish SOS with details and remain in the scheduler loop.

## Bootstrap Layer Architecture

----------------------------------

### 5.1 Immortal Bootstrap Design

The bootstrap layer runs a cooperative scheduler that never blocks and never yields control to the app indefinitely. It owns the single MQTT client, routes messages to the app, and orchestrates OTA safely by quiescing the app before applying updates.

### 5.2 Bootstrap Manager Functions

Key responsibilities include:
* Application lifecycle (init/tick/shutdown) and supervision
* Error recovery and SOS
* MQTT ownership, routing, LWT, and health
* OTA update coordination (quiesce → apply → reset)
* Help mode with responsive MQTT pumping

### 5.3 HTTP Update System

- Updater writes only app/shared files; bootstrap files are protected.
- Recommended write strategy: write to temporary file then rename to final path to reduce partial write risks.
- After successful apply, a device reset ensures clean imports of updated modules.

## Update and Deployment Strategy

---------------------------------

### 6.2 HTTP-Based Update System

**Device Update Process (Bootstrap-Owned):**
1. Bootstrap receives MQTT `update` command
2. Publishes `update_received` and `updating`
3. Requests app `shutdown()` and waits briefly
4. Downloads and applies application/shared files via HTTP (never bootstrap)
5. Publishes `updated`
6. Resets device to load new code

### 6.3 Update Safety Mechanisms

* Bootstrap isolation and single MQTT client authority
* App quiesce before writes; short timeout to proceed if app is unresponsive
* Immediate feedback via status and SOS
* Reset after update to guarantee clean reload

## Implementation Phases

-------------------------

### 12.1 Phase 1: Bootstrap Infrastructure

- Implement non-blocking bootstrap scheduler (loop + MQTT pump)
- Introduce runtime API and app lifecycle (init/tick/shutdown)
- Centralize MQTT in bootstrap with message routing and LWT
- Keep OTA strictly in bootstrap with quiesce → apply → reset

### 12.2 Phase 2: Device Integration

- Refactor device apps (e.g., `garage-controller`) to plugin lifecycle
- Replace app-owned MQTT clients with runtime API usage
- Validate command responsiveness (fast callbacks) and periodic telemetry in `tick()`

### 12.3 Phase 3: Production Deployment

- Flash bootstrap once; deploy app-only updates via OTA
- Server-driven manifests remain unchanged
- Run drills: app fault, network drop, OTA failure → verify SOS and recovery

## Error Handling and Reliability

---------------------------------

### 7.1 Multi-Layer Error Handling

- Bootstrap catches all app exceptions and continues running
- App reports issues via `runtime.sos()`; bootstrap publishes SOS
- OTA failures do not crash the bootstrap; system remains up and subscribes to updates

### 7.3 Device Health Monitoring

- Health heartbeat originates from the bootstrap to avoid duplication
- App can optionally publish device-local telemetry health (not system health)

## Testing Strategy

------------------

### 8.1 Unit Testing

- Test individual components (e.g., MQTT client, OTA updater) in isolation
- Validate runtime API usage and app lifecycle hooks

### 8.2 Integration Testing

- Test device apps with simulated MQTT and runtime API
- Validate OTA update flows and error handling

### 8.3 System Testing

- Test complete system with multiple devices and server
- Validate end-to-end functionality and error recovery

## Runtime API

--------------

### 9.1 Runtime API Overview

The runtime API provides a set of functions for the app to interact with the bootstrap and MQTT.

### 9.2 Runtime API Functions

```text
runtime.publish(topic: str, payload: str|bytes, retain: bool = False) -> bool
runtime.subscribe(topic: str, callback: Callable[[str, bytes], None], fast: bool = False) -> None
runtime.unsubscribe(topic: str) -> None
runtime.sos(error: str, message: str = "") -> None
runtime.now_ms() -> int
runtime.log(level: str, msg: str) -> None  # optional convenience
```

## Scheduler Loop

--------------

### 10.1 Scheduler Loop Overview

The scheduler loop is the main loop of the bootstrap that runs at a high frequency.

### 10.2 Scheduler Loop Functions

- Update LED based on state
- Ensure WiFi connected (backoff)
- Ensure MQTT connected; publish LWT and boot/version on connect
- Pump MQTT messages and dispatch to system/app handlers
- Publish periodic health (e.g., every 30s)
- Call `app.tick()` if app is initialized (must return quickly)

## Message Routing

--------------

### 11.1 Message Routing Overview

The message routing system is responsible for dispatching MQTT messages to the app.

### 11.2 Message Routing Functions

- Subscribe to system topics and any app-registered topics
- Dispatch app topics to registered callbacks
- Handle MQTT message pump and routing to system/app handlers

## OTA Flow

------------

### 12.1 OTA Flow Overview

The OTA flow is responsible for updating the app via HTTP.

### 12.2 OTA Flow Functions

- Trigger: server publishes manifest to `home/system/{device_id}/update`
- Bootstrap sequence:
  1) Publish `status=update_received`
  2) Publish `status=updating`
  3) Quiesce the app: call `app.shutdown(reason="update")` with a short timeout (e.g., 1–2s)
  4) Download and apply files via `HttpUpdater` (protect bootstrap files)
  5) Publish `status=updated`
  6) `machine.reset()` to reload updated modules cleanly
- On any failure during OTA: publish SOS with details and remain in the scheduler loop.