# IRIS Android App Design Spec

Date: 2025-08-24
Status: Draft v1
Owner: Mobile

## Vision
A real-time command center for the IRIS home system. The app emphasizes speed, density of information, and a modern, futuristic "JARVIS" vibe: holographic layers, neon accents, glass blur, subtle particle/motion effects, and AI-assisted interactions.

---

## Visual Design Guidelines

- **Color System (Dark-first)**
  - Primary: `#00E5FF` (Neon Cyan)
  - Secondary: `#7C4DFF` (Neon Purple)
  - Accent: `#00FF8E` (Neon Green)
  - Danger: `#FF4D4D` (Alert Red)
  - Warning: `#FFC107` (Amber)
  - Background: `#0A0F1A` (Deep Space), Elevated Surface: `#0F1524`, Overlay Glass: rgba(255,255,255,0.06)
  - Text High: `#E6F7FF`, Text Medium: `#A9C1CC`, Muted: `#6C7A80`

- **Typography**
  - Display/Hero: Orbitron (Google Fonts) – techno/geometric
  - Body/UI: Inter or Roboto Flex – crisp and highly legible
  - Mono (metrics/logs): JetBrains Mono
  - Usage in RN: via `@expo-google-fonts/*` packages; fallbacks to system fonts

- **Shape & Effects**
  - Corners: 12–16px radius
  - Strokes: 1px hairline borders with gradient edges (cyan→purple) sparingly
  - Shadows/Glows: outer neon glow for interactive elements on focus/active
  - Glassmorphism: blurred backdrops for HUD panels; maintain contrast ratio WCAG AA

- **Iconography**
  - Phosphor Icons (duotone) or Material Symbols (rounded); stroke-based with glow on active

- **Motion**
  - Micro-animations: 150–220ms ease-in-out
  - Realtime pulse on live metrics (e.g., heartbeat ring around device tiles)
  - Physics-based pull-to-refresh on feeds

- **Data Density**
  - Grid-based dashboard composed of responsive cards
  - Each card contains: main value/state, secondary stats, actions (1–3), status chip

- **Theme Implementation (React Native Paper / MD3)**
  - Start from MD3 dark theme; override colors with above palette.
  - Provide theme tokens in `android/app/src/shared/theme.ts` (to be created) with light variant.

---

## Information Architecture

- **Primary Screen: Command Center (Home)**
  - Purpose: Zero-navigation control of critical functions with live readouts.
  - Layout: 2-column grid (phones) / 3-column (tablets). Top area shows global alerts and power status.
  - Cards (tap opens details; long-press opens quick actions):
    - Garage Door: State chip (open/closed/opening/closing/error), actions: Toggle.
    - Flood Light: State chip (on/off), action: On, Off, Toggle.
    - Weather (Garage BMP388): Temperature °F, Pressure inHg; note: humidity N/A with current sensor.
    - Freezer (Garage DS18B20): Temperature °F, min/max, action: Thresholds.
    - House Freezer (House Monitor): Temperature °F, Door status; action: Thresholds.
    - Power: City power status (online/offline), last heartbeat.
    - SOS Incidents: Count of active, acknowledge/resolve quick actions.
    - Devices Health: Per-device status chips; tap to device details.
    - Updates: Trigger OTA to device/group; show last result.

- **Secondary Screens**
  - Garage
    - Door timeline, event history, safety interlocks, manual controls.
    - Light scheduling, auto-off, sunrise/sunset rules.
  - Weather
    - Trend charts (temp, pressure), sampling rate, sensor diagnostics.
  - Freezer
    - Current temp, thresholds, alerts, historical chart, sensor health.
  - SOS
    - Active incidents list, details (error, timestamp, device), action: trigger update/reboot, add notes, mark resolved.
  - Devices
    - Registry view (/api/devices), per-device detail (status, version, last seen/boot, RSSI), commands (reboot, update).
  - Updates
    - Group updates, progress stream, history.
  - Settings
    - Auth/session, notification prefs (FCM), themes, network/API endpoints, debug tools.

---

## Data and API Mapping

Current server API (`server/api/main.py`):
- GET `/api/garage/weather` → WeatherState {temperature_f, pressure_inhg}
- GET `/api/garage/freezer` → FreezerState {temperature_f}
- GET `/api/garage/door/state` → DoorState {state}
- POST `/api/garage/door/{command}` → open|close|toggle
- POST `/api/garage/light/{state}` → on|off; POST `/api/garage/light/toggle`
- GET `/api/devices` → Dict[str, DeviceInfo]
- POST `/api/devices/{device_id}/reboot`
- WebSocket `/ws/device-status` → heartbeat/ping-pong for now (future push updates)

MQTT topics (design targets in `design_doc.md`):
- `home/garage/door/status|command`
- `home/garage/light/status|command`
- `home/garage/weather/temperature|pressure`
- `home/garage/freezer/temperature`
- `home/power/city/status|heartbeat` (planned)
- `home/freezer/door/status|ajar_time` (planned for house monitor)
- `home/system/{device_id}/(update|reboot|ping|status|health|sos|version)`

Client should consume REST for initial MVP; add WebSocket for live updates v2.

---

## Feature List and User Stories

- **Global**
  - As a user, I can view a summary of critical stats (power, SOS, devices, garage door state, temps, light) on one screen.
  - As a user, I receive push notifications for SOS and thresholds (FCM).
  - As an admin, I can authenticate and manage preferences.

- **Garage Door**
  - Open, Close, Toggle door via buttons with confirmation haptics.
  - See live door state; show large unsafe/error indicator if both reeds active.
  - See last motion time and recent events timeline.

- **Flood Light**
  - On/Off/Toggle with immediate feedback; optional auto-off timer.

- **Weather (Garage)**
  - See temperature °F and pressure inHg live; charts for last 24h/7d.
  - Placeholder for humidity (hidden until sensor supports it).

- **Freezer (Garage)**
  - See temperature °F; set upper/lower thresholds; receive alerts on breach.
  - View historical chart and sensor diagnostics (DS18B20 ROM, last read time).

- **House Monitor (Future/Parallel)**
  - See house freezer temp and door status (open/closed, ajar time).
  - Configure alerts for door ajar > N seconds.

- **Power**
  - See city power status (online/offline) and last heartbeat timestamp.
  - Notification on outage/restore.

- **SOS Management**
  - View active SOS incidents; tap into details with device info, error, timestamp.
  - Send update/reboot commands; add resolution notes; mark resolved.

- **Devices**
  - List all devices with status, last seen, version, RSSI.
  - Per-device actions: reboot, trigger update, view logs (future).

- **Updates**
  - Trigger OTA update for single device or group; see progress and result.

- **Settings**
  - Login/session, API base URL, theme (JARVIS dark default, optional light), notifications.

---

## UI Layout: Command Center (Draft)

- Header: IRIS logo, connection chip (API/WebSocket), profile.
- Alert Row: SOS banner (if any), power status chip, device health summary.
- Grid Cards (quick actions in each):
  - Garage Door (primary action: Toggle; secondary: Open/Close)
  - Flood Light (primary: Toggle)
  - Weather (temp, pressure)
  - Freezer Garage (temp + thresholds)
  - House Freezer (temp + door)
  - SOS (active count + acknowledge)
  - Devices (online/offline count)
  - Updates (trigger)
- Bottom Bar: Tabs for Home, Devices, SOS, History, Settings (5 tabs max)

---

## Technical Notes

- **Stack**: Expo (RN), React Native Paper, expo-fonts, react-native-svg, Reanimated 3, React Query (data), Zustand or Redux Toolkit (state), Socket.IO or native WS for live.
- **Networking**: Use REST endpoints above; encapsulate in `services/api.ts` with `fetch` and React Query. WS connects after auth.
- **Theming**: `theme.ts` exporting Paper MD3 theme with custom tokens; wrap App in `Provider`.
- **State**: Device cache kept in memory; derive "critical" tile values from reducers/selectors.
- **Performance**: 60fps interactions; use FlatList/FlashList for feeds; memoized cards; lightweight SVG sparklines in tiles.
- **Accessibility**: Minimum 4.5:1 for text; reduce motion option; haptic feedback on critical actions.

---

## Open Questions / Next Steps

- Confirm authentication model (JWT from FastAPI, stored securely; refresh flow).
- Decide on humidity sensor addition or hide UI field until implemented.
- Define WS message schema for live tile updates.
- Define OTA update API endpoints (server TODOs in `TASK.md`).

---

## Appendix: Mapping to Repository

- Server endpoints referenced from `server/api/main.py`.
- MQTT topics referenced from `design_doc.md` 4.1.
- Devices covered: `devices/garage-controller/app/main.py`, `devices/house-monitor/app/`.
- This spec drives tasks under `TASK.md` → Phase 2: Mobile App Development.
