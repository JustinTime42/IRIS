from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Optional, Dict, Any, Tuple
import paho.mqtt.client as mqtt
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path
import hashlib
from dateutil import parser as dateutil_parser  # type: ignore

"""
Database imports: handle both package and direct execution contexts.
"""
try:
    # When running with project root in PYTHONPATH
    from server.database.init import init_db, db_health_check
    from server.database.engine import get_session
    from server.database.engine import AsyncSessionLocal
    from server.database.repositories import (
        upsert_device,
        log_device_boot,
        record_sensor_reading,
        create_sos_incident,
        get_weather_history,
    )
except Exception:
    # Fallback when running from within server/ directory
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from database.init import init_db, db_health_check  # type: ignore
    from database.engine import get_session  # type: ignore
    from database.engine import AsyncSessionLocal  # type: ignore
    from database.repositories import (  # type: ignore
        upsert_device,
        log_device_boot,
        record_sensor_reading,
        create_sos_incident,
        get_weather_history,
    )

# Async utilities
import asyncio

# Global handle to the running event loop for scheduling DB work from MQTT thread
_event_loop: Optional[asyncio.AbstractEventLoop] = None


async def process_mqtt_event(topic: str, payload: str) -> None:
    """Persist relevant MQTT events into the database.

    Args:
        topic (str): MQTT topic
        payload (str): Decoded payload
    """
    try:
        async with AsyncSessionLocal() as session:  # type: ignore
            # System topics: home/system/{device_id}/{type}
            if topic.startswith("home/system/"):
                parts = topic.split('/')
                if len(parts) >= 4:
                    device_id = parts[2]
                    msg_type = parts[3]

                    if msg_type == 'health':
                        await upsert_device(session, device_id=device_id, status=payload)
                    elif msg_type == 'sos':
                        details = json.loads(payload) if payload else {}
                        await upsert_device(
                            session,
                            device_id=device_id,
                            status=DeviceStatus.NEEDS_HELP.value,
                            last_error=details.get('message') or details.get('error') or 'Unknown error',
                        )
                        await create_sos_incident(
                            session,
                            device_id=device_id,
                            error_message=details.get('message') or details.get('error'),
                            details=details,
                        )
                    elif msg_type == 'boot':
                        try:
                            boot_dt = datetime.utcfromtimestamp(int(payload) / 1000)
                        except Exception:
                            boot_dt = datetime.utcnow()
                        await upsert_device(session, device_id=device_id, last_boot=boot_dt)
                        await log_device_boot(session, device_id=device_id, boot_time=boot_dt)
                    elif msg_type == 'version':
                        await upsert_device(session, device_id=device_id, version=payload)

            # Garage and other topics → record as sensor readings
            elif topic == GARAGE_LIGHT_TOPIC:
                await record_sensor_reading(session, device_id=GARAGE_DEVICE_ID, metric='garage_light', value_text=payload)
            elif topic == GARAGE_DOOR_STATUS_TOPIC:
                await record_sensor_reading(session, device_id=GARAGE_DEVICE_ID, metric='garage_door', value_text=payload)
            elif topic == GARAGE_WEATHER_TEMPERATURE_TOPIC:
                try:
                    await record_sensor_reading(session, device_id=GARAGE_DEVICE_ID, metric='garage_temperature_f', value_float=float(payload))
                except Exception:
                    pass
            elif topic == GARAGE_WEATHER_PRESSURE_TOPIC:
                try:
                    await record_sensor_reading(session, device_id=GARAGE_DEVICE_ID, metric='garage_pressure_inhg', value_float=float(payload))
                except Exception:
                    pass
            elif topic == GARAGE_FREEZER_TEMPERATURE_TOPIC:
                try:
                    await record_sensor_reading(session, device_id=GARAGE_DEVICE_ID, metric='freezer_temperature_f', value_float=float(payload))
                except Exception:
                    pass
    except Exception as ex:
        logger.error(f"process_mqtt_event failed for topic={topic}: {ex}")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT Settings
# Use 'mqtt' when running in Docker, 'localhost' when running locally
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# Associate garage-originated readings with this device_id (must exist in devices table)
# Override via env GARAGE_DEVICE_ID if your device_id differs (e.g., 'garage-controller')
GARAGE_DEVICE_ID = os.getenv("GARAGE_DEVICE_ID", "garage-controller")

# OTA Repo Settings
# If OTA_RAW_BASE is set, it should include the trailing ref or path prefix as needed.
# Otherwise, we build raw GitHub URLs using ORG/REPO and ref.
OTA_RAW_BASE = os.getenv("OTA_RAW_BASE", "").rstrip("/")  # e.g., https://your-server/ota/raw
GITHUB_ORG = os.getenv("GITHUB_ORG", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_DEFAULT_REF = os.getenv("GITHUB_DEFAULT_REF", "main")

# Repository root resolution
def _resolve_project_root() -> Path:
    """Resolve the monorepo root path.

    Order:
    1) PROJECT_ROOT env var (if exists)
    2) Walk up from this file to find a directory that has both 'devices/' and 'shared/'
    3) Fallback to parent of the 'api' directory (../) or current parent
    """
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        if p.exists():
            return p
    here = Path(__file__).resolve()
    # Iterate safely over available parents only
    for cand in here.parents:
        try:
            if (cand / "devices").exists() and (cand / "shared").exists():
                return cand
        except Exception:
            # Ignore unexpected FS errors and continue searching
            pass
    # Fallback: parent of api dir if present
    try:
        api_parent = here.parent.parent if here.parent.name == "api" else here.parent
        return api_parent
    except Exception:
        return here.parent

PROJECT_ROOT = _resolve_project_root()
logger.debug(f"Resolved PROJECT_ROOT to {PROJECT_ROOT}")

# Device Status Models
class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    NEEDS_HELP = "needs_help"
    UPDATING = "updating"
    ERROR = "error"

class DeviceInfo(BaseModel):
    device_id: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    last_seen: Optional[datetime] = None
    version: Optional[str] = None
    last_error: Optional[str] = None
    last_boot: Optional[datetime] = None
    ip_address: Optional[str] = None
    rssi: Optional[int] = None  # WiFi signal strength
    last_error_code: Optional[str] = None

# In-memory device registry
device_registry: Dict[str, DeviceInfo] = {}

class AlertItem(BaseModel):
    """Structured current alert for a device.

    Attributes:
        device_id: Source device identifier
        code: Machine-friendly code for the error (e.g., "ds18b20_read_error")
        message: Human-readable message (optional)
        last_seen: When this alert was last updated
    """
    device_id: str
    code: str
    message: Optional[str] = None
    last_seen: datetime

# Map of (device_id, code) -> latest AlertItem
current_alerts: Dict[tuple[str, str], AlertItem] = {}

def update_device_status(device_id: str, **updates) -> DeviceInfo:
    """Update device status in the registry."""
    now = datetime.utcnow()
    if device_id not in device_registry:
        device_registry[device_id] = DeviceInfo(device_id=device_id, last_seen=now)
    
    device = device_registry[device_id]
    for key, value in updates.items():
        if hasattr(device, key):
            setattr(device, key, value)
    
    # Always update last seen on any update
    device.last_seen = now
    return device

# MQTT Topics (matching Pico W implementation)
# GARAGE_DEVICE_ID is configured above; do not override here.
GARAGE_LIGHT_TOPIC = 'home/garage/light/status'  # From Pico W to server
GARAGE_LIGHT_COMMAND_TOPIC = 'home/garage/light/command'  # From server to Pico W
GARAGE_DOOR_STATUS_TOPIC = 'home/garage/door/status'
GARAGE_DOOR_COMMAND_TOPIC = 'home/garage/door/command'  # From server to Pico W
GARAGE_WEATHER_TEMPERATURE_TOPIC = 'home/garage/weather/temperature'
GARAGE_WEATHER_PRESSURE_TOPIC = 'home/garage/weather/pressure'
GARAGE_FREEZER_TEMPERATURE_TOPIC = 'home/garage/freezer/temperature'

# Garage Light State (simplified to match Pico W's string format)
class LightState(BaseModel):
    state: str  # 'on' or 'off'
    last_updated: Optional[str] = None

# In-memory storage for light state (in production, use a database)
garage_light_state = LightState(state="off")

# Additional in-memory sensor caches
class WeatherState(BaseModel):
    temperature_f: Optional[float] = None
    pressure_inhg: Optional[float] = None
    last_updated: Optional[datetime] = None


class FreezerState(BaseModel):
    temperature_f: Optional[float] = None
    last_updated: Optional[datetime] = None


class DoorState(BaseModel):
    state: Optional[str] = None  # 'open' | 'closed' | 'opening' | 'closing' | 'error'
    last_updated: Optional[datetime] = None


weather_state = WeatherState()
freezer_state = FreezerState()
door_state = DoorState()

def _derive_error_code(details: Dict[str, Any]) -> str:
    """Derive a machine-friendly error code from SOS details.

    Tries `details['code']`, then `details['error']` or `details['message']`,
    slugging to snake_case.
    """
    raw = details.get('code') or details.get('error') or details.get('message') or 'unknown_error'
    try:
        s = str(raw).strip().lower()
        # Replace non-alphanum with underscores and collapse repeats
        import re
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s).strip('_')
        return s or 'unknown_error'
    except Exception:
        return 'unknown_error'

def update_light_state(new_state: Dict[str, Any]):
    """Update the in-memory light state."""
    global garage_light_state
    # Convert string state to dict if needed
    if isinstance(new_state, str):
        new_state = {"state": new_state}
    garage_light_state = LightState(**{**garage_light_state.dict(), **new_state})
    return garage_light_state

# MQTT Client Setup
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logger.info("Connected to MQTT Broker!")
        # Subscribe to system and garage topics
        client.subscribe("home/system/+/#")  # All system topics for all devices
        client.subscribe(GARAGE_LIGHT_TOPIC)
        client.subscribe(GARAGE_DOOR_STATUS_TOPIC)
        client.subscribe("home/garage/weather/#")
        client.subscribe("home/garage/freezer/#")
        logger.info(
            "Subscribed to MQTT topics: home/system/+/#, %s, %s, %s, %s",
            GARAGE_LIGHT_TOPIC,
            GARAGE_DOOR_STATUS_TOPIC,
            "home/garage/weather/#",
            "home/garage/freezer/#",
        )
    else:
        logger.error(f"Failed to connect to MQTT Broker with code: {reason_code}")

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages."""
    topic = msg.topic
    payload = msg.payload.decode()
    logger.debug(f"Received `{payload}` from `{topic}` topic")
    
    try:
        # Handle system topics (home/system/<device_id>/<type>)
        if topic.startswith("home/system/"):
            parts = topic.split('/')
            if len(parts) >= 4:  # home/system/<device_id>/<type>
                device_id = parts[2]
                msg_type = parts[3]
                
                if msg_type == 'health':
                    update_device_status(device_id, status=DeviceStatus(payload))
                elif msg_type == 'sos':
                    error_info = json.loads(payload) if payload else {}
                    code = _derive_error_code(error_info)
                    now = datetime.utcnow()
                    current_alerts[(device_id, code)] = AlertItem(
                        device_id=device_id,
                        code=code,
                        message=error_info.get('message') or error_info.get('error'),
                        last_seen=now,
                    )
                    update_device_status(
                        device_id,
                        status=DeviceStatus.NEEDS_HELP,
                        last_error=error_info.get('message', 'Unknown error'),
                        last_error_code=code,
                    )
                elif msg_type == 'boot':
                    update_device_status(
                        device_id,
                        last_boot=datetime.utcfromtimestamp(int(payload) / 1000)
                    )
                elif msg_type == 'version':
                    update_device_status(device_id, version=payload)
        
        # Handle garage light state
        elif topic == GARAGE_LIGHT_TOPIC:
            update_light_state(payload)
        # Handle door status
        elif topic == GARAGE_DOOR_STATUS_TOPIC:
            try:
                door_state.state = payload
                door_state.last_updated = datetime.utcnow()
            except Exception:
                pass
        # Handle weather topics
        elif topic == GARAGE_WEATHER_TEMPERATURE_TOPIC:
            try:
                weather_state.temperature_f = float(payload)
                weather_state.last_updated = datetime.utcnow()
            except Exception:
                logger.warning(f"Invalid temperature payload: {payload}")
        elif topic == GARAGE_WEATHER_PRESSURE_TOPIC:
            try:
                weather_state.pressure_inhg = float(payload)
                weather_state.last_updated = datetime.utcnow()
            except Exception:
                logger.warning(f"Invalid pressure payload: {payload}")
        # Handle freezer topic
        elif topic == GARAGE_FREEZER_TEMPERATURE_TOPIC:
            try:
                freezer_state.temperature_f = float(payload)
                freezer_state.last_updated = datetime.utcnow()
            except Exception:
                logger.warning(f"Invalid freezer temp payload: {payload}")
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MQTT message: {payload}")
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")
        logger.exception(e)
    finally:
        # Schedule DB persistence on the app's event loop
        try:
            if _event_loop is not None:
                asyncio.run_coroutine_threadsafe(process_mqtt_event(topic, payload), _event_loop)
        except Exception as ex:
            logger.error(f"Failed to schedule DB task for topic {topic}: {ex}")

# Application Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MQTT client...")
    
    # Initialize MQTT client with explicit API version
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
    except Exception as e:
        logger.error(f"Failed to initialize MQTT client: {e}")
        raise
    
    if MQTT_USERNAME and MQTT_PASSWORD:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()
        app.state.mqtt_client = mqtt_client
        logger.info("MQTT client started successfully")
    except Exception as e:
        logger.error(f"Failed to start MQTT client: {e}")
        raise
    
    # Initialize database (create tables if not present)
    try:
        logger.info("Initializing database (creating tables if needed)...")
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Capture event loop for cross-thread scheduling
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    
    # Ensure the garage device row exists so sensor_readings FK constraints are satisfied
    try:
        async with AsyncSessionLocal() as session:  # type: ignore
            await upsert_device(session, device_id=GARAGE_DEVICE_ID)
            logger.info("Ensured Device row exists for device_id=%s", GARAGE_DEVICE_ID)
    except Exception as e:
        logger.warning("Could not ensure default device exists (%s): %s", GARAGE_DEVICE_ID, e)
     
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down MQTT client...")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    logger.info("MQTT client shut down")

# Create FastAPI app
app = FastAPI(
    title="IRIS Home Automation API",
    description="API for the IRIS (Intelligent Residence Information System)",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mqtt_connected": app.state.mqtt_client.is_connected() if hasattr(app.state, 'mqtt_client') else False
    }

# Root Endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to IRIS Home Automation API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Database health endpoint
@app.get("/db/health")
async def db_health():
    """Simple database health check returning server version."""
    try:
        result = await db_health_check()
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

# Garage Light Endpoints
@app.post("/api/garage/light/toggle", response_model=LightState)
async def toggle_garage_light():
    """Toggle the garage light state."""
    try:
        # Toggle the light state
        new_state = "on" if garage_light_state.state == "off" else "off"
        
        # Publish the command to MQTT (simple string 'on' or 'off')
        app.state.mqtt_client.publish(GARAGE_LIGHT_COMMAND_TOPIC, new_state)
        
        # Update local state
        updated_state = update_light_state({"state": new_state, "last_updated": "now"})
        
        logger.info(f"Toggled garage light to {new_state}")
        return updated_state
    except Exception as e:
        logger.error(f"Error toggling garage light: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/garage/light/state", response_model=LightState)
async def get_garage_light_state():
    """Get the current garage light state."""
    return garage_light_state

# New sensor endpoints
@app.get("/api/garage/weather", response_model=WeatherState)
async def get_garage_weather():
    """Get latest weather readings from BMP388 (temperature °F and pressure inHg)."""
    return weather_state


@app.get("/api/garage/freezer", response_model=FreezerState)
async def get_freezer_temperature():
    """Get latest freezer temperature (°F)."""
    return freezer_state


@app.get("/api/garage/door/state", response_model=DoorState)
async def get_garage_door_state():
    """Get the current garage door state."""
    return door_state

@app.post("/api/garage/door/{command}")
async def send_garage_door_command(command: str):
    """Send a command to the garage door controller.

    Args:
        command (str): One of "open", "close", or "toggle".

    Returns:
        dict: Status response with echoed command.
    """
    cmd = (command or "").lower()
    if cmd not in ("open", "close", "toggle"):
        raise HTTPException(status_code=400, detail="Command must be 'open', 'close', or 'toggle'")

    # Ensure MQTT client is connected
    if not hasattr(app.state, 'mqtt_client') or not app.state.mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT client not connected")

    try:
        app.state.mqtt_client.publish(GARAGE_DOOR_COMMAND_TOPIC, cmd)
        logger.info(f"Sent garage door command: {cmd}")
        return {"status": "sent", "command": cmd}
    except Exception as e:
        logger.error(f"Error sending garage door command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/garage/light/{state}", response_model=LightState)
async def set_garage_light_state(state: str):
    """Set the garage light to a specific state (on/off)."""
    state = state.lower()
    if state not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="State must be 'on' or 'off'")
    
    try:
        # Publish the command to MQTT (simple string 'on' or 'off')
        app.state.mqtt_client.publish(GARAGE_LIGHT_COMMAND_TOPIC, state)
        
        # Update local state
        updated_state = update_light_state({"state": state, "last_updated": "now"})
        
        logger.info(f"Set garage light to {state}")
        return updated_state
    except Exception as e:
        logger.error(f"Error setting garage light state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Device Management Endpoints

class OTAUpdateRequest(BaseModel):
    """Request body for triggering an OTA update.
    
    Attributes:
        ref (str | None): Git ref to retrieve files from (branch or commit SHA). Defaults to env default.
    """
    ref: Optional[str] = None

def _iter_device_files(device_id: str) -> list[Tuple[str, str]]:
    """Enumerate repo file paths that should be deployed for a device.
    
    Args:
        device_id (str): Target device identifier.
    
    Returns:
        list[tuple[str, str]]: Tuples of (repo_path, device_path).
    """
    results: list[Tuple[str, str]] = []
    # Include device-specific app files
    device_app_dir = PROJECT_ROOT / "devices" / device_id / "app"
    if device_app_dir.is_dir():
        for p in device_app_dir.rglob("*"):
            if p.is_file() and _include_in_ota(p):
                rel = p.relative_to(PROJECT_ROOT).as_posix()
                # Map devices/{device_id}/app/<...> -> app/<...>
                sub = p.relative_to(device_app_dir).as_posix()
                results.append((rel, f"app/{sub}"))
    # Include shared modules
    shared_dir = PROJECT_ROOT / "shared"
    if shared_dir.is_dir():
        for p in shared_dir.rglob("*"):
            if p.is_file() and _include_in_ota(p):
                rel = p.relative_to(PROJECT_ROOT).as_posix()
                sub = p.relative_to(shared_dir).as_posix()
                results.append((rel, f"shared/{sub}"))
    return results

def _include_in_ota(path: Path) -> bool:
    """Return True if the file path should be included in OTA manifests.
    
    Excludes caches and bootstrap files by convention.
    """
    name = path.name
    if name in {".DS_Store", "Thumbs.db"}:
        return False
    if name.endswith((".pyc", ".pyo")):
        return False
    parts = set(path.parts)
    if "__pycache__" in parts:
        return False
    # Guard: never include bootstrap files
    try:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
    except Exception:
        rel = path.as_posix()
    if rel.startswith("devices/bootstrap/"):
        return False
    if name in {"main.py", "bootstrap_manager.py", "http_updater.py"} and path.parent == PROJECT_ROOT:
        return False
    return True

def _raw_url_for(repo_path: str, ref: str) -> str:
    """Construct a raw URL for a given repo path and ref.
    
    If OTA_RAW_BASE is configured, use it as base (server proxy). Otherwise use GitHub raw URLs.
    """
    if OTA_RAW_BASE:
        # Expect server to accept /<ref>/<path> or similar; keep simple: base + /<ref>/<repo_path>
        return f"{OTA_RAW_BASE}/{ref}/{repo_path}"
    if not (GITHUB_ORG and GITHUB_REPO):
        raise RuntimeError("GITHUB_ORG and GITHUB_REPO must be set or OTA_RAW_BASE provided")
    return f"https://raw.githubusercontent.com/{GITHUB_ORG}/{GITHUB_REPO}/{ref}/{repo_path}"

def _build_update_manifest(device_id: str, ref: Optional[str]) -> Dict[str, Any]:
    """Build the OTA update payload for a device.
    
    Args:
        device_id (str): Target device id.
        ref (str | None): Branch name or commit SHA. Defaults to env.
    
    Returns:
        dict: Payload with "files" list containing url/path entries.
    """
    use_ref = (ref or GITHUB_DEFAULT_REF).strip()
    entries: list[Dict[str, Any]] = []
    
    def _size_and_sha256(abs_path: Path) -> Tuple[int, str]:
        try:
            size = abs_path.stat().st_size
        except Exception:
            size = 0
        sha = ""
        try:
            h = hashlib.sha256()
            with open(abs_path, "rb") as fp:
                for chunk in iter(lambda: fp.read(65536), b""):
                    if not chunk:
                        break
                    h.update(chunk)
            sha = h.hexdigest()
        except Exception:
            sha = ""
        return size, sha
    
    for repo_path, device_path in _iter_device_files(device_id):
        abs_path = PROJECT_ROOT / repo_path
        size, sha = _size_and_sha256(abs_path)
        entry: Dict[str, Any] = {
            "url": _raw_url_for(repo_path, use_ref),
            "path": device_path,
        }
        # Only include validators when available to keep backward-compat flexible
        if size:
            entry["size"] = size
        if sha:
            entry["sha256"] = sha
        entries.append(entry)
    if not entries:
        logger.error("OTA manifest empty for device_id=%s at PROJECT_ROOT=%s (ref=%s)", device_id, str(PROJECT_ROOT), use_ref)
        raise HTTPException(status_code=404, detail=f"No deployable files found for device_id='{device_id}' at PROJECT_ROOT='{PROJECT_ROOT}'")
    logger.debug(f"Built OTA manifest for device_id={device_id} with {len(entries)} files")
    return {"files": entries}

@app.get("/api/devices/{device_id}/update/manifest")
async def get_update_manifest(device_id: str, ref: Optional[str] = None):
    """Preview the OTA manifest for a device without publishing.
    
    Args:
        device_id (str): Target device id.
        ref (str | None): Branch or commit SHA.
    
    Returns:
        dict: Update payload with file list.
    """
    try:
        return _build_update_manifest(device_id, ref)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to build manifest for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/devices/{device_id}/update")
async def trigger_device_update(device_id: str, req: OTAUpdateRequest):
    """Trigger OTA update for a device by publishing a generated manifest to MQTT.
    
    Args:
        device_id (str): Target device id.
        req (OTAUpdateRequest): Optional ref for code version to use.
    
    Returns:
        dict: Publish status and file count.
    """
    # Ensure MQTT client is connected
    if not hasattr(app.state, 'mqtt_client') or not app.state.mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT client not connected")

    try:
        payload = _build_update_manifest(device_id, req.ref)
        topic = f"home/system/{device_id}/update"
        sent = app.state.mqtt_client.publish(topic, json.dumps(payload))
        logger.info("Published OTA update for %s with %d files (ref=%s)", device_id, len(payload.get("files", [])), (req.ref or GITHUB_DEFAULT_REF))
        return {"status": "published", "device_id": device_id, "file_count": len(payload.get("files", [])), "ref": req.ref or GITHUB_DEFAULT_REF, "mqtt_result": getattr(sent, 'rc', 0)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish OTA for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices", response_model=Dict[str, DeviceInfo])
async def list_devices():
    """List all registered devices and their status."""
    return device_registry

@app.get("/api/devices/{device_id}", response_model=DeviceInfo)
async def get_device_status(device_id: str):
    """Get detailed status for a specific device."""
    if device_id not in device_registry:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_registry[device_id]

@app.post("/api/devices/{device_id}/reboot")
async def reboot_device(device_id: str):
    """Send a reboot command to the device."""
    if not hasattr(app.state, 'mqtt_client') or not app.state.mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="MQTT client not connected")
    
    topic = f"home/system/{device_id}/reboot"
    try:
        app.state.mqtt_client.publish(topic, "")
        return {"status": "reboot_command_sent", "device_id": device_id}
    except Exception as e:
        logger.error(f"Failed to send reboot command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/current")
async def get_current_alerts() -> List[AlertItem]:
    """Return the most recent instance of each (device_id, code) alert.

    This avoids accumulation; if a given device keeps sending the same code, we only keep the latest.
    """
    # Sort by last_seen descending for convenience
    return sorted((item for item in current_alerts.values()), key=lambda x: x.last_seen, reverse=True)

# WebSocket endpoint for real-time updates
@app.websocket("/ws/device-status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Just keep the connection open; we'll push updates as they come
            # Client can send a ping to check if the connection is still alive
            await websocket.receive_text()
            await websocket.send_json({"status": "pong"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/api/garage/weather/history")
async def get_garage_weather_history(
    start: Optional[str] = None,
    end: Optional[str] = None,
    range: Optional[str] = None,
    bucket: str = "hour",
    session=Depends(get_session),
):
    """Return historical weather readings aggregated by time bucket.

    Args:
        start (str | None): ISO8601 start time (UTC). If omitted, uses now - range (or 24h).
        end (str | None): ISO8601 end time (UTC). Defaults to now.
        range (str | None): Convenience like '24h', '7d', '30d'. Ignored when start provided.
        bucket (str): 'minute' | 'hour' | 'day'. Defaults to 'hour'.

    Returns:
        list[dict]: [{ ts, temperature_f, pressure_inhg }]
    """
    try:
        now = datetime.utcnow()
        # Parse end
        end_dt = dateutil_parser.isoparse(end).replace(tzinfo=None) if end else now
        # Determine start
        if start:
            start_dt = dateutil_parser.isoparse(start).replace(tzinfo=None)
        else:
            # Parse range like '24h', '7d', default 24h
            amount = 24
            unit = 'h'
            if range:
                try:
                    import re
                    m = re.fullmatch(r"(\d+)([mhdw])", range.strip().lower())
                    if m:
                        amount = int(m.group(1))
                        unit = m.group(2)
                except Exception:
                    pass
            from datetime import timedelta
            mult = { 'm': timedelta(minutes=1), 'h': timedelta(hours=1), 'd': timedelta(days=1), 'w': timedelta(weeks=1) }[unit]
            start_dt = end_dt - amount * mult

        data = await get_weather_history(session, start=start_dt, end=end_dt, bucket=bucket)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"weather history failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
