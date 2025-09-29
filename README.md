# IRIS - Intelligent Residence Information System

IRIS is a home automation system built around Raspberry Pi Pico W microcontrollers with a bulletproof two-tier firmware architecture, a centralized Linux server, and future mobile/web clients. The design emphasizes an immutable bootstrap layer on each device (for recovery, updates, and health) and a replaceable application layer (device-specific logic deployed over the air).

Note: The repository folder on disk may still be named `corvids-nest`.

High-level goals (see `design_doc.md` for details):
- Resilient OTA updates using a permanent bootstrap and HTTP downloads
- MQTT hub-and-spoke messaging for telemetry, control, health, and SOS
- Single monorepo for devices, server, and clients with selective deployment
- Human-in-the-loop recovery through SOS signaling and device health tracking

What lives in this repo today:
- Pico W bootstrap components that never change over OTA (`devices/bootstrap/`)
- Shared MicroPython modules for WiFi/MQTT/config (`shared/`)
- Device-specific app directories (`devices/<device_id>/app/`)
- Deployment automation to flash/update devices via `mpremote` (`deployment/scripts/deploy.py`)
- Server, mobile, and web scaffolding directories to grow into

Current device plan (from `design_doc.md`):
- City Power Monitor: Detect city power presence (via device online status and heartbeat)
- Freezer Monitor: DS18B20 temperature + reed switch door ajar timing
- Garage Controller: Garage door relay + position, flood light relay, weather, freezer temp

Current implementation snapshot:
- Bootstrap layer present and deployable: `devices/bootstrap/{main.py, bootstrap_manager.py, http_updater.py}`
- Shared modules present: `shared/{wifi_manager.py, mqtt_client.py, config_manager.py}`
- Device apps:
  - `garage-controller`: Minimal blink app to validate handoff (`devices/garage-controller/app/main.py`)
  - `house-monitor`: Placeholder scaffold for freezer and city power monitoring (`devices/house-monitor/app/{main.py, sensors.py}`)
  - City power monitor (standalone device): planned
- Server stack: directories created under `server/` (API, DB, alerts, monitoring, MQTT) — not implemented yet
- Client apps: placeholders under `android/` and `web/` — not implemented yet

MQTT topic design (abridged; see `design_doc.md` §4.1 for full tree):
- `home/system/{device_id}/...` → update, status, sos, health, version
  - status values now include: `running`, `update_received`, `updating`, `updated`, `alive`
- `home/power/city/...` → status, heartbeat (city power presence)
- `home/freezer/...` → temperature readings and door status/ajar time
- `home/garage/...` → door status/commands, light status/commands, weather

Deployment overview:
- Merge `deployment/common/network.json` with per-device `deployment/devices/<device>/device.json` (gitignored) and upload as `:/config/device.json`
- Copy bootstrap to device root, shared modules to `:/shared/`, and the selected device app to `:/app/`
- Soft reset the Pico to start bootstrap → app handoff

Status at a glance:
- Implemented: Bootstrap files; shared WiFi/MQTT/config modules; deploy script; minimal `garage-controller` app; `house-monitor` scaffold
- Planned: Full device logic (sensors/relays), server API+DB+alerts, mobile app, dashboard, advanced SOS/health analytics

## Quick Commands

See `COMMANDS.md` for copy-paste-ready commands to:
- Monitor all MQTT topics
- Restart Docker services/stack
- Build the Android app (APK/AAB)

## Repository Structure

- `devices/bootstrap/` — Immortal bootstrap layer (never OTA-updated)
- `devices/<device_id>/app/` — Device-specific application code; deployed to the device as `/app/`
- `shared/` — Reusable MicroPython modules (WiFi, MQTT, config)
- `deployment/common/network.json` — Shared WiFi + MQTT settings
- `deployment/devices/<device>/device.json` — Per-device config with at least `device_id` (gitignored)
- `deployment/device_index.json` — Maps `device_id` to its config path and metadata
- `deployment/scripts/deploy.py` — Deployment script that pushes code + merged config via `mpremote`

## Prerequisites

- Python 3.8+
- `mpremote` installed: `pip install mpremote`
- Fill `deployment/common/network.json` with WiFi + MQTT values
- Create per-device config (e.g., `deployment/devices/garage-controller-01/device.json`):

```json
{
  "device_id": "garage-controller"
}
```

Ensure `deployment/device_index.json` has an entry pointing to that file.

## Deployment

1. Connect the Pico W over USB.
2. Run the deploy script:

```bash
python deployment/scripts/deploy.py
```

3. Select the device from the list (based on `deployment/device_index.json`).
4. Select the detected Pico port (or enter it manually).
5. The script will:
   - Merge `deployment/common/network.json` + selected `device.json` (device overrides) and upload to `:/config/device.json`
   - Copy bootstrap files to device root
   - Copy `shared/` to `:/shared/`
   - Copy `devices/<device_id>/app/` to `:/app/` (if present)
   - Reset the device

## On-Device Behavior

- Bootstrap loads `/config/device.json` and connects to WiFi/MQTT.
- Publishes LWT, boot, version, and periodic health to MQTT.
- Imports `app.main.main()` from `/app/main.py` and runs it.
- Listens for update commands to refresh application files via HTTP and publishes OTA progress:
  - `home/system/{device_id}/status` = `update_received` immediately when the command is received
  - `home/system/{device_id}/status` = `updating` while applying files
  - `home/system/{device_id}/status` = `updated` after a successful apply
  - On errors, an SOS is published to `home/system/{device_id}/sos` with details
- Garage Controller: Flood light relay defaults to ON at boot to ensure light availability immediately after power-up. You can change it via MQTT command/topic `home/garage/light/command` ("on"/"off"/"toggle").

## Troubleshooting

- Missing WiFi/MQTT: Fix `deployment/common/network.json`, re-deploy.
- Wrong device_id: Fix per-device `device.json`, re-deploy.
- Shared imports fail: Ensure `/shared/` exists on the device and contains `__init__.py`.
- App not running: Ensure `devices/<device_id>/app/main.py` defines `main()`.
- mpremote: "could not enter raw repl":
  - Ensure no other app (e.g., Thonny, serial monitor) is using the port.
  - Unplug/replug the Pico W or press RESET; then re-run the deploy.
  - Confirm the correct port is selected (e.g., `COM5` on Windows).
  - The deploy script now auto-resets and retries transfers, but persistent failures usually indicate the port is busy or the cable/port is unstable.

## OTA Update Automation (Server-Driven)

The server can now generate file manifests for a given `device_id` and publish them to the device's existing OTA topic without modifying the bootstrap. This implements the "Option A" flow where the server walks the repo to gather relevant files for the device.

Environment variables:
- `GITHUB_ORG` and `GITHUB_REPO`: used to construct GitHub raw URLs
- `GITHUB_DEFAULT_REF` (default: `main`): default branch or commit SHA for manifests
--OR-
- `OTA_RAW_BASE`: if set, the server will build file URLs as `{OTA_RAW_BASE}/{ref}/{repo_path}` (useful for private repos via a proxy)
- `PROJECT_ROOT`: optional override of the repo root path for server discovery (defaults to project root)

Endpoints:
- `GET /api/devices/{device_id}/update/manifest?ref=<branch-or-sha>`
  - Returns a JSON payload `{ files: [ { url, path }, ... ] }`
  - Includes `devices/{device_id}/app/**` mapped to `app/**` and `shared/**` mapped to `shared/**`
- `POST /api/devices/{device_id}/update` with body `{ "ref": "<branch-or-sha>" }`
  - Publishes the same manifest to `home/system/{device_id}/update` via MQTT

Example (preview manifest):
```bash
curl "http://localhost:8000/api/devices/garage-controller/update/manifest?ref=main"
```

Example (trigger OTA publish):
```bash
curl -X POST "http://localhost:8000/api/devices/garage-controller/update" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main"}'
```

Notes:
- The Pico W bootstrap still only accepts the standard manifest payload with `files: [ { url, path } ]` and applies app-layer files. It will ignore bootstrap paths.
- Use a commit SHA in `ref` for reproducible deployments.
- For private repos, set `OTA_RAW_BASE` to a server proxy that serves raw bytes to the device.

## Mobile App (Android / Expo)

The React Native app lives in `android/app/`. See design at `android/APP_DESIGN.md`.

### Prereqs
- Node 18+
- Expo CLI (optional): `npm i -g expo-cli`
- Android Emulator or Expo Go on device
- Server running locally at `http://localhost:8000` (configurable in `android/app/src/shared/config.ts`)

### First-time setup
```powershell
cd android/app
npm install
```

### Run
```powershell
npm run web      # quick web preview
npm run android  # open Android emulator or use Expo Go
```

### Notes
- Theme tokens are in `android/app/src/shared/theme.ts`.
- Navigation is in `android/app/src/navigation/RootNavigator.tsx`.
- API client: `android/app/src/services/api.ts` (maps to `server/api/main.py`).
- React Query hooks: `android/app/src/hooks/useGarage.ts`.
- Adjust backend base URL in `android/app/src/shared/config.ts`.

## Security Notes

- `deployment/devices/**/device.json` is gitignored to avoid committing secrets.
- Consider keeping `deployment/common/network.json` private if it contains real credentials.
