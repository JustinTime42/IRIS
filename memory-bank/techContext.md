# Tech Context - IRIS

## Technologies Used

### Microcontroller Platform

**Raspberry Pi Pico W**

- ARM Cortex-M0+ dual-core processor
- 264KB SRAM, 2MB Flash
- 2.4GHz 802.11n wireless
- MicroPython runtime environment
- GPIO for sensors and relays

### Programming Languages

- **MicroPython**: Device firmware (bootstrap and applications)
- **Python 3.8+**: Server backend (FastAPI, database, services)
- **TypeScript/JavaScript**: React Native mobile app
- **SQL**: Database queries and schema
- **Kotlin**: Future Android widget development

### Server Stack

#### MQTT Broker

**Mosquitto 2.0+**

- Lightweight message broker
- Supports QoS levels 0, 1, 2
- Last Will and Testament (LWT)
- Retained messages
- Authentication via password file

#### Database

**PostgreSQL 13+**

- Time-series data storage
- JSON support for complex payloads
- Efficient indexing for queries
- Docker volume for persistence

#### API Framework

**FastAPI**

- Modern Python web framework
- Automatic OpenAPI documentation
- WebSocket support
- Async request handling
- Pydantic for data validation

#### Containerization

**Docker & Docker Compose**

- Service orchestration
- Environment variable management
- Volume mounting for persistence
- Network isolation
- Easy local development

### Mobile Development

#### Framework

**React Native with Expo**

- Cross-platform mobile development
- Hot reload for rapid iteration
- Native module access
- Push notification support

#### UI Library

**React Native Paper**

- Material Design components
- Theming support
- Responsive layouts
- Accessibility features

#### State Management

**React Query (TanStack Query)**

- Server state synchronization
- Caching and background refetching
- Optimistic updates
- Error handling

#### Navigation

**React Navigation**

- Tab-based navigation
- Stack navigation within tabs
- Deep linking support
- TypeScript integration

### Development Tools

#### Version Control

**Git & GitHub**

- Single repository structure
- Branch protection
- Pull request workflow
- GitHub Actions (future CI/CD)

#### IDE/Editor

**Windsurf AI Code Editor**

- AI-assisted development
- Integrated terminal
- Git integration
- Extension support

#### Device Deployment

**mpremote**

- MicroPython remote control
- File transfer to Pico W
- REPL access
- Soft reset capability

#### API Testing

**curl & Postman**

- REST endpoint testing
- WebSocket testing
- Request/response debugging
- Environment variables

## Development Setup

### Prerequisites Installation

#### Windows 11 Environment

```powershell
# Python for server and tools
winget install Python.Python.3.11

# Node.js for mobile app
winget install OpenJS.NodeJS.LTS

# Docker Desktop for server stack
winget install Docker.DockerDesktop

# Git for version control
winget install Git.Git
```

#### Python Dependencies

```bash
# Server dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary
pip install paho-mqtt python-dateutil
pip install pytest pytest-asyncio

# Device deployment
pip install mpremote
```

#### Node.js Dependencies

```bash
# Mobile app dependencies
cd android/app
npm install

# Global tools
npm install -g expo-cli eas-cli
```

### Environment Configuration

#### Network Configuration

`deployment/common/network.json`:

```json
{
  "wifi": {
    "ssid": "YOUR_WIFI_SSID",
    "password": "YOUR_WIFI_PASSWORD"
  },
  "mqtt": {
    "broker": "YOUR_SERVER_IP",
    "port": 1883,
    "username": "device",
    "password": "YOUR_MQTT_PASSWORD"
  }
}
```

#### Device Configuration

`deployment/devices/{device-name}/device.json`:

```json
{
  "device_id": "unique-device-id",
  "hardware": {
    "pins": {
      "led": 25,
      "sensor": 28
    }
  }
}
```

#### Docker Environment

`.env` file for docker-compose:

```env
POSTGRES_DB=home_automation
POSTGRES_USER=hauser
POSTGRES_PASSWORD=secure_password
MQTT_USERNAME=device
MQTT_PASSWORD=mqtt_password
API_PORT=8000
```

## Technical Constraints

### Hardware Limitations

- **Memory**: 264KB SRAM limits concurrent operations
- **Storage**: 2MB Flash requires efficient code
- **Processing**: Single-threaded MicroPython
- **Network**: WiFi-only connectivity
- **Power**: Must handle power cycles gracefully

### Network Constraints

- **Bandwidth**: Limited by WiFi quality
- **Latency**: Local network RTT affects responsiveness
- **Reliability**: Must handle disconnections
- **Security**: WPA2 minimum, no open networks
- **Topology**: All devices must reach MQTT broker

### Software Constraints

- **MicroPython**: Subset of Python 3.4+
- **No Threading**: Cooperative multitasking only
- **Import Limits**: Careful module management
- **GC Pressure**: Regular garbage collection needed
- **File System**: FAT with no journaling

## Dependencies

### MicroPython Modules (Built-in)

```python
import machine      # Hardware access
import network     # WiFi connectivity
import utime       # Time functions
import ujson       # JSON parsing
import uos         # OS functions
import gc          # Garbage collection
```

### Server Python Packages

```txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
paho-mqtt==1.6.1
python-dateutil==2.8.2
pydantic==2.5.0
```

### Mobile App NPM Packages

```json
{
  "dependencies": {
    "expo": "~49.0.0",
    "react": "18.2.0",
    "react-native": "0.72.6",
    "react-native-paper": "^5.10.0",
    "@react-navigation/native": "^6.1.0",
    "@tanstack/react-query": "^5.0.0",
    "expo-notifications": "~0.20.1"
  }
}
```

## Tool Usage Patterns

### Device Development Workflow

1. **Edit Code**: Modify MicroPython files locally
2. **Deploy**: Use `mpremote` to upload to device
3. **Test**: Monitor MQTT topics for output
4. **Debug**: Use REPL for interactive debugging
5. **Commit**: Push stable changes to Git

### Server Development Workflow

1. **Edit Code**: Modify Python API files
2. **Restart**: Docker compose restart service
3. **Test**: Use curl or Postman for API
4. **Monitor**: Check Docker logs for errors
5. **Database**: Use pgAdmin for queries

### Mobile Development Workflow

1. **Edit Code**: Modify React Native components
2. **Hot Reload**: See changes instantly
3. **Test**: Use Expo Go or emulator
4. **Debug**: React Native Debugger
5. **Build**: EAS Build for production

### Deployment Commands

#### Device Deployment

```bash
# Full deployment
python deployment/scripts/deploy.py

# Quick file update
mpremote connect COM5 cp app/main.py :/app/main.py

# Soft reset
mpremote connect COM5 soft-reset
```

#### Server Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Database migration
docker exec -it postgres psql -U hauser -d home_automation
```

#### Mobile Deployment

```bash
# Development server
npm run start

# Android build
eas build --platform android

# Web preview
npm run web
```

## Security Considerations

### Network Security

- WPA2/WPA3 encrypted WiFi
- VPN for remote access
- No port forwarding
- Local network isolation

### MQTT Security

- Username/password authentication
- TLS encryption (future)
- Topic-based ACLs (future)
- Rate limiting

### API Security

- CORS configuration
- Input validation
- SQL injection prevention
- Rate limiting (future)

### Device Security

- No hardcoded credentials
- Secure config storage
- OTA signature verification (future)
- Bootstrap protection

## Performance Optimization

### Device Optimization

- Minimize import statements
- Use integer math when possible
- Buffer MQTT messages
- Periodic garbage collection
- Efficient string handling

### Server Optimization

- Database indexing
- Query optimization
- Connection pooling
- Caching strategy
- Async operations

### Network Optimization

- MQTT QoS selection
- Message batching
- Retained message usage
- Topic hierarchy design
- Compression (future)
