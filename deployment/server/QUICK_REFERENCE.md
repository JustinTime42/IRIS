# Server Deployment Quick Reference

## Initial Setup (One Time Only)

### On Linux Server

1. Copy `setup-server.sh` to the server:

   ```powershell
   scp deployment\server\setup-server.sh justin@<server-ip>:~/
   ```

2. SSH to server and run setup:

   ```bash
   ssh justin@<server-ip>
   chmod +x ~/setup-server.sh
   ~/setup-server.sh
   ```

3. Create/edit .env file:
   ```bash
   nano /opt/corvids-nest/server/.env
   ```

### On Windows Desktop

1. Add production remote:

   ```powershell
   cd C:\Users\justi\Code\corvids-nest
   git remote add production justin@<server-ip>:/opt/corvids-nest/.git
   ```

2. Verify SSH access:
   ```powershell
   ssh justin@<server-ip> "echo Connected successfully"
   ```

## Daily Deployment

### Deploy Changes

```powershell
cd C:\Users\justi\Code\corvids-nest
.\deployment\server\deploy.ps1
```

This will:

- Show uncommitted changes
- Ask to commit them
- Push to server
- Automatically rebuild and restart services

### Deploy with Custom Message

```powershell
.\deployment\server\deploy.ps1 -CommitMessage "Fixed bug in API"
```

### Deploy Without Committing

```powershell
.\deployment\server\deploy.ps1 -SkipCommit
```

## Monitoring & Debugging

### View Logs (from Windows)

```powershell
# All services
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs -f"

# Just API
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs -f api"

# Just MQTT
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs -f mqtt"

# Last 100 lines
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs --tail=100"
```

### Check Service Status

```powershell
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose ps"
```

### Check API Health

```powershell
# From Windows (replace <server-ip> with your Tailscale IP)
curl http://<server-ip>:8000/health

# Or test via SSH
ssh justin@<server-ip> "curl http://localhost:8000/health"
```

### Restart Services

```powershell
# Restart all services
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose restart"

# Restart just API
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose restart api"

# Full rebuild and restart
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose up -d --build --force-recreate"
```

## Server Management

### Start/Stop Services

```powershell
# Using systemd (recommended for production)
ssh justin@<server-ip> "sudo systemctl start corvids-nest"
ssh justin@<server-ip> "sudo systemctl stop corvids-nest"
ssh justin@<server-ip> "sudo systemctl status corvids-nest"

# Using docker compose directly
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose up -d"
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose down"
```

### Database Management

```powershell
# Access PostgreSQL
ssh justin@<server-ip> "docker exec -it iris-db psql -U postgres -d iris"

# Backup database
ssh justin@<server-ip> "docker exec iris-db pg_dump -U postgres iris > ~/iris-backup-$(date +%Y%m%d).sql"

# Access PGAdmin
# Open browser: http://<server-ip>:5050
```

### MQTT Testing

```powershell
# Subscribe to all topics (requires mosquitto_sub on server)
ssh justin@<server-ip> "mosquitto_sub -h localhost -t '#' -v"

# Publish test message
ssh justin@<server-ip> "mosquitto_pub -h localhost -t 'home/test' -m 'Hello'"
```

## Rapid Development Workflow

For rapid iteration without Git commits:

### Option 1: Direct Edit on Server

```bash
ssh justin@<server-ip>
cd /opt/corvids-nest/server
nano api/main.py  # Edit file
docker compose restart api  # Restart to apply changes
```

### Option 2: Rsync from Windows

```powershell
# Sync just the server directory
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' `
  C:\Users\justi\Code\corvids-nest\server\ `
  justin@<server-ip>:/opt/corvids-nest/server/

# Restart services
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose restart api"
```

### Option 3: Quick Deploy Script

For frequent small changes:

```powershell
# Quick deploy function - add to your PowerShell profile
function Deploy-Quick {
    param([string]$msg = "Quick update")
    cd C:\Users\justi\Code\corvids-nest
    git add .
    git commit -m $msg
    .\deployment\server\deploy.ps1 -SkipCommit
}

# Usage
Deploy-Quick "Fixed typo"
```

## Troubleshooting

### Deployment Failed

```powershell
# Check what's wrong on server
ssh justin@<server-ip> "cd /opt/corvids-nest && git status"
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs"

# Force reset server to match your code
ssh justin@<server-ip> "cd /opt/corvids-nest && git reset --hard HEAD"
```

### Container Won't Start

```powershell
# Check logs
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs api"

# Check .env file
ssh justin@<server-ip> "cat /opt/corvids-nest/server/.env"

# Rebuild from scratch
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose down -v && docker compose up -d --build"
```

### SSH Connection Issues

```powershell
# Verify Tailscale is running
tailscale status

# Test basic SSH
ssh justin@<server-ip> "echo Success"

# Check SSH key
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh justin@<server-ip> "cat >> ~/.ssh/authorized_keys"
```

### Git Push Rejected

```powershell
# View server's Git status
ssh justin@<server-ip> "cd /opt/corvids-nest && git log -5 --oneline"

# Force push (CAREFUL!)
.\deployment\server\deploy.ps1 -Force
```

## Useful Aliases

Add to your PowerShell profile (`$PROFILE`):

```powershell
# Quick access to corvids-nest
function cn { Set-Location C:\Users\justi\Code\corvids-nest }



# Quick deploy
function deploy {
    cn
    .\deployment\server\deploy.ps1 @args
}

# View server logs
function server-logs {
    ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs -f $args"
}

# SSH to server
function server {
    ssh justin@<server-ip>
}

# Check server status
function server-status {
    ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose ps"
}
```

Usage:

```powershell
cn                          # cd to project
deploy                      # Deploy
server-logs api             # View API logs
server                      # SSH to server
server-status               # Check status
```

## Environment Variables Reference

Required in `/opt/corvids-nest/server/.env`:

```bash
# API Settings
API_DEBUG=false
API_SECRET_KEY=<generate-random-key>
API_ALGORITHM=HS256
API_ACCESS_TOKEN_EXPIRE_MINUTES=30
PROJECT_ROOT=/app

# MQTT Settings
MQTT_BROKER_HOST=mqtt
MQTT_BROKER_PORT=1883
MQTT_USERNAME=<your-username>
MQTT_PASSWORD=<secure-password>

# Database Settings
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=iris
POSTGRES_HOST=db
POSTGRES_PORT=5432

# PGAdmin Settings
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=<secure-password>

# Logging
LOG_LEVEL=INFO

# GitHub (for OTA updates to Pico W)
GITHUB_ORG=JustinTime42
GITHUB_REPO=IRIS
GITHUB_DEFAULT_REF=main
```

Generate secure passwords:

```powershell
# Random password
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

# Or use a password manager
```
