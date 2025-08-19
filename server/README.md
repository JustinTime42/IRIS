# IRIS Home Automation Server

This is the central server for the IRIS (Intelligent Residence Information System) home automation system. It includes an MQTT broker, FastAPI backend, and PostgreSQL database.

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

## Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your configuration:
   - Set secure passwords for MQTT and PostgreSQL
   - Adjust other settings as needed

3. Create required directories:
   ```bash
   mkdir -p mosquitto/{config,data,log}
   mkdir -p logs
   ```

4. Start the services:
   ```bash
   docker-compose up -d
   ```

## Services

- **API Server**: http://localhost:8000
  - API Documentation: http://localhost:8000/docs
  - Health Check: http://localhost:8000/health

- **MQTT Broker**:
  - Host: `localhost`
  - Port: `1883`
  - WebSocket: `ws://localhost:9001`

- **Database**:
  - Host: `localhost`
  - Port: `5432`
  - Database: `iris`
  - Username/Password: As set in `.env`

- **PGAdmin**: http://localhost:5050
  - Email/Password: As set in `.env`

## Development

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn api.main:app --reload
   ```

## Project Structure

```
server/
├── api/                   # FastAPI application
│   └── main.py           # Main application entry point
├── mosquitto/            # MQTT broker configuration
│   └── config/
│       └── mosquitto.conf
├── .env.example          # Example environment variables
├── .env                  # Local environment variables (gitignored)
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile.api        # API server Dockerfile
└── requirements.txt      # Python dependencies
```

## Security Notes

1. Change all default passwords in production
2. Enable MQTT authentication in production
3. Use HTTPS in production
4. Regularly update dependencies

## License

[Your License Here]
