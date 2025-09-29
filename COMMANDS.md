# IRIS Command Quick Reference

This document provides copy-paste-ready commands for common tasks in this repository.

Notes

- Assumes Windows 11 with PowerShell.
- Run Docker commands from the `server/` directory unless otherwise noted.
- MQTT broker runs via Docker Compose as service `mqtt` (container `iris-mqtt`) on `localhost:1883` per `server/docker-compose.yml`.

---

## Monitor all MQTT channels

docker compose exec --% mqtt sh -lc "mosquitto_sub -h localhost -p 1883 -u \"$MQTT_USERNAME\" -P \"$MQTT_PASSWORD\" -v -t \"#\""

# Inside container (uses $MQTT_USERNAME/$MQTT_PASSWORD from .env):

mosquitto_sub -h localhost -p 1883 -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -t '#' -v

## Restart Docker containers / stack

From `server/` directory:

```powershell
cd server
# Restart the whole stack (mqtt, api, db, pgadmin)
docker compose restart

# Restart just the API service
docker compose restart api

# Restart just the MQTT broker
docker compose restart mqtt

# Rebuild API image and start (use after code changes to API dependencies)
docker compose up -d --build api

# Start entire stack in background (if not already running)
docker compose up -d

# View service logs (follow)
docker compose logs -f api
```

If Docker Desktop is not running, start it first, then rerun the above commands.

---

## Build the full Android app package

This repo uses a React Native app (see `android/`). Two build paths are provided:

A) Local Gradle build (generates a release APK)

```powershell
# In repo root
cd android
# Install dependencies (use the package manager your project uses)
# npm ci   # or: yarn install

# Build release (Windows uses gradlew.bat)
./gradlew.bat assembleRelease

# Output APK:
# android/app/build/outputs/apk/release/app-release.apk
```

B) Expo EAS Cloud Build (generates a Play Store AAB)

Requirements

- Expo/EAS project configured; sign in with `eas login`.
- EAS CLI installed: `npm i -g eas-cli` (or use npx: `npx eas-cli@latest --version`).

```powershell
# From repo root (or android app directory)
# Configure once (if not already):
# npx expo prebuild        # only if transitioning to bare workflow
# npx expo-doctor

# Production build (Android AAB)
npx eas build -p android --profile production

# After completion, EAS provides a URL to download the .aab
```

Notes

- Use Path A (Gradle) to sideload and test on device quickly (APK).
- Use Path B (EAS) for distribution to Play Store (AAB), credentials managed by EAS.
- If using a managed Expo workflow exclusively, prefer EAS builds.

---

## Appendix: Useful paths and names

- Docker Compose file: `server/docker-compose.yml`
  - Services/containers:
    - `mqtt` → container `iris-mqtt` (ports 1883, 9001)
    - `api` → container `iris-api` (port 8000)
    - `db` → container `iris-db` (port 5432)
    - `pgadmin` → container `iris-pgadmin` (port 5050)
- Android release APK (local Gradle): `android/app/build/outputs/apk/release/app-release.apk`
- MQTT topic root: `home/` (see `design_doc.md` → 4.1 MQTT Topic Structure)
