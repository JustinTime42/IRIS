# Product Context - IRIS

## Why This Project Exists

### The Problem

Living in Alaska with frequent power outages and extreme weather conditions creates unique challenges for home management. Critical systems like freezers can fail silently, garage doors can malfunction in harsh conditions, and knowing the status of city power versus generator power is essential for managing resources. Traditional home automation systems are either too complex, too expensive, or not resilient enough for Alaska's challenging environment.

### The Vision

IRIS provides peace of mind through intelligent monitoring and control of critical home systems. It's designed specifically for harsh environments where reliability matters most, power outages are common, and remote management is essential. The system continues operating even during partial failures, automatically recovers from disruptions, and always keeps humans informed when intervention is needed.

## User Experience Goals

### Primary Users

- **Homeowner**: Needs reliable monitoring of critical systems, instant alerts for problems, and simple controls
- **Remote Manager**: Family member or caretaker who helps monitor the home from afar
- **Maintenance Personnel**: Needs clear diagnostic information when fixing issues

### Core User Journeys

#### Daily Monitoring

1. Open mobile app to see at-a-glance status
2. View current temperatures, door states, power status
3. Receive proactive alerts if anything needs attention
4. Take action directly from the app when needed

#### Emergency Response

1. Receive critical alert (freezer too warm, door left open)
2. Open app to see detailed status and context
3. Take corrective action remotely if possible
4. Coordinate on-site response if needed

#### Remote Control

1. Need to open garage for delivery/visitor
2. Open app and tap garage door control
3. See real-time status updates as door moves
4. Confirm final position through sensors

## How It Should Work

### System Behavior

#### Normal Operation

- Devices continuously monitor sensors and report telemetry
- Server aggregates data and tracks trends
- Mobile app displays current status and recent history
- Alerts trigger only for actionable issues

#### During Power Outage

- Generator-backed devices continue operating
- City power monitor reports outage immediately
- System tracks outage duration for records
- Automatic recovery when power returns

#### During Network Issues

- Devices buffer critical data locally
- Automatic reconnection attempts with backoff
- SOS messages sent when connection restored
- No data loss for critical events

#### During Device Failures

- Bootstrap layer remains operational
- SOS messages provide diagnostic details
- Other devices continue operating independently
- Clear guidance for troubleshooting

### Alert Philosophy

#### Alert Levels

1. **Critical**: Immediate action required (freezer warming, door stuck)
2. **Warning**: Attention needed soon (sensor trending bad, low battery)
3. **Info**: Awareness only (power restored, update completed)

#### Alert Delivery

- Push notifications to mobile devices
- In-app alert center with history
- Email for critical alerts (backup channel)
- Future: Voice alerts via smart speakers

## Product Principles

### Reliability First

Every design decision prioritizes system reliability. Features that could compromise core monitoring are rejected. The system must work when needed most - during emergencies and harsh conditions.

### Human-Centered Automation

Automation assists but never replaces human judgment. The system provides information, suggestions, and convenient controls, but humans make the decisions. Clear feedback confirms every action.

### Progressive Disclosure

Simple status for daily use, detailed diagnostics when needed. The interface adapts to the situation - minimal during normal operation, comprehensive during troubleshooting.

### Fail-Safe Design

When something goes wrong, the system fails in a safe, predictable way. Garage doors don't open unexpectedly. Freezer monitoring continues even if other features fail. Bootstrap always recovers.

## Success Metrics

### Reliability Metrics

- 99.9% uptime for critical monitoring
- < 60 second alert delivery time
- Zero data loss for critical events
- 100% recovery from network disruptions

### User Experience Metrics

- < 3 taps to any critical action
- < 2 seconds app load time
- Clear status visible within 1 second
- Zero false positive critical alerts

### System Health Metrics

- All devices reporting within 5 minutes
- OTA updates complete within 10 minutes
- SOS messages resolved within 24 hours
- Bootstrap recovery 100% successful

## Future Vision

### Phase 1 (Current)

- Core monitoring and control
- Mobile app for management
- Alert system for critical issues
- OTA update capability

### Phase 2 (Planned)

- Historical trending and analytics
- Predictive maintenance alerts
- Integration with weather services
- Voice control via LLM

### Phase 3 (Future)

- Multi-home support
- Sharing with family/caretakers
- Energy usage optimization
- Smart automation rules
