# Corvids Nest Deployment

This directory contains deployment scripts and configuration for the Corvids Nest (IRIS) home automation system.

## Structure

```
deployment/
├── server/                          # Linux server deployment
│   ├── DEPLOYMENT_SETUP.md         # Complete setup guide
│   ├── QUICK_REFERENCE.md          # Common commands
│   ├── deploy.ps1                  # Windows deployment script
│   └── setup-server.sh             # Linux server setup script
├── devices/                         # Pico W device configurations
├── scripts/
│   └── deploy.py                   # Pico W deployment script
└── device_index.json               # Device registry
```

## Quick Start

### Server Deployment (First Time)

1. **On Linux Server** - Copy and run setup script:
   ```powershell
   scp deployment\server\setup-server.sh justin@<server-ip>:~/
   ssh justin@<server-ip>
   chmod +x ~/setup-server.sh
   ~/setup-server.sh
   ```

2. **On Windows Desktop** - Add Git remote:
   ```powershell
   git remote add production justin@<server-ip>:/opt/corvids-nest/.git
   ```

3. **Deploy!**
   ```powershell
   .\deployment\server\deploy.ps1
   ```

### Pico W Deployment

```bash
python deployment/scripts/deploy.py
```

## Documentation

- **[DEPLOYMENT_SETUP.md](server/DEPLOYMENT_SETUP.md)** - Complete server deployment setup guide
- **[QUICK_REFERENCE.md](server/QUICK_REFERENCE.md)** - Common commands and workflows

## Architecture

### Server Deployment
- **Method**: Git push with post-receive hook
- **Transport**: SSH over Tailscale VPN
- **Automation**: Automatic docker compose rebuild on push
- **Services**: FastAPI, PostgreSQL, MQTT (Mosquitto), PGAdmin

### Device Deployment
- **Method**: USB serial via mpremote
- **Target**: Raspberry Pi Pico W microcontrollers
- **Structure**: Bootstrap layer + application layer
- **Updates**: OTA via HTTP (GitHub API) for application layer

## Workflows

### Production Release
1. Make changes locally
2. Test thoroughly
3. Commit changes
4. Run `.\deployment\server\deploy.ps1`
5. Verify via logs and health check

### Rapid Development
1. Make changes locally
2. Use rsync to sync to server
3. Restart services without commit
4. Test, iterate, commit when ready

### Device Updates
1. Update device code in `devices/<device-name>/app/`
2. Commit to repository
3. Trigger OTA update via mobile app or API
4. Device downloads from GitHub and updates itself

## Security

- **No exposed ports**: All access via Tailscale VPN
- **SSH keys**: Public key authentication required
- **Environment secrets**: `.env` files excluded from Git
- **Encrypted transport**: Tailscale provides WireGuard encryption

## Monitoring

### Health Checks
- API: `http://<server>:8000/health`
- Database: `http://<server>:8000/db/health`
- MQTT: Port 1883 (local) / 9001 (WebSocket)

### Logs
```powershell
# From Windows
ssh justin@<server> "cd /opt/corvids-nest/server && docker compose logs -f"

# Specific service
ssh justin@<server> "cd /opt/corvids-nest/server && docker compose logs -f api"
```

### Status
```powershell
ssh justin@<server> "cd /opt/corvids-nest/server && docker compose ps"
```

## Backup

### Database
```bash
ssh justin@<server> "docker exec iris-db pg_dump -U postgres iris > ~/iris-backup-$(date +%Y%m%d).sql"
```

### Configuration
- `.env` file (backup separately, not in Git)
- Device configurations in `deployment/devices/`
- All code in Git repository

## Troubleshooting

### Deployment Failed
1. Check server logs: `ssh justin@<server> "cd /opt/corvids-nest && git status"`
2. Verify .env exists: `ssh justin@<server> "cat /opt/corvids-nest/server/.env"`
3. Check Docker: `ssh justin@<server> "docker ps"`

### Services Won't Start
1. Check logs: `docker compose logs`
2. Verify .env configuration
3. Check disk space: `df -h`
4. Rebuild: `docker compose up -d --build --force-recreate`

### Can't Connect to Server
1. Verify Tailscale is running
2. Check SSH key: `ssh justin@<server> "echo Success"`
3. Test basic connectivity: `ping <server>`

## Support Files

- **[Complete Parts List](../Complete%20Home%20Automation%20Project%20Parts%20List%20-%20Updated.md)**
- **[Design Documentation](../Updated%20Home%20Automation%20Design%20Doc.md)**
- **[Main README](../README.md)**
