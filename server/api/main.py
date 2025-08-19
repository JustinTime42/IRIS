from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt
import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

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

# In-memory device registry
device_registry: Dict[str, DeviceInfo] = {}

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
GARAGE_LIGHT_TOPIC = 'home/garage/light/status'  # From Pico W to server
GARAGE_LIGHT_COMMAND_TOPIC = 'home/garage/light/command'  # From server to Pico W

# Garage Light State (simplified to match Pico W's string format)
class LightState(BaseModel):
    state: str  # 'on' or 'off'
    last_updated: Optional[str] = None

# In-memory storage for light state (in production, use a database)
garage_light_state = LightState(state="off")

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
        logger.info(f"Subscribed to MQTT topics: home/system/+/#, {GARAGE_LIGHT_TOPIC}")
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
                    update_device_status(
                        device_id,
                        status=DeviceStatus.NEEDS_HELP,
                        last_error=error_info.get('message', 'Unknown error')
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
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MQTT message: {payload}")
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")
        logger.exception(e)

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
