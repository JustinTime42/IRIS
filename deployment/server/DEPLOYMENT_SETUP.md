# Server Deployment Setup Guide

This guide walks you through setting up remote deployment from your Windows desktop to the Linux server in your garage.

## Prerequisites

1. **Tailscale VPN**: Already installed and running (you should have this based on your design docs)
2. **SSH Access**: Ensure you can SSH to the Linux server
3. **Git**: Installed on both machines
4. **Docker and Docker Compose**: Already installed on Linux server

## Step 1: Initial Server Setup

SSH into your Linux server (replace `<server-ip>` with your Tailscale IP or hostname):

```bash
ssh justin@<server-ip>
```

### 1.1: Create Deployment Directory

```bash
# Create the deployment directory
sudo mkdir -p /opt/corvids-nest
sudo chown $USER:$USER /opt/corvids-nest
cd /opt/corvids-nest

# Initialize as Git repository
git init
git config receive.denyCurrentBranch ignore
```

### 1.2: Create Post-Receive Hook

This hook automatically deploys when you push changes:

```bash
# Create the hook file
cat > /opt/corvids-nest/.git/hooks/post-receive << 'EOF'
#!/bin/bash
set -e

echo "===== Starting deployment ====="
cd /opt/corvids-nest

# Force checkout to update working directory
git reset --hard HEAD

# Navigate to server directory
cd server

echo "===== Stopping services ====="
docker compose down

echo "===== Building and starting services ====="
docker compose up -d --build

echo "===== Deployment complete! ====="
echo "Services are now running. Check status with: docker compose ps"
EOF

# Make it executable
chmod +x /opt/corvids-nest/.git/hooks/post-receive
```

### 1.3: Set Up Environment Variables

```bash
cd /opt/corvids-nest/server

# Copy your .env file if you haven't already
# This should contain your production settings
nano .env
```

Make sure your `.env` has production-ready values (don't commit this file!).

### 1.4: Initial Deployment

```bash
cd /opt/corvids-nest/server

# Create required directories
mkdir -p mosquitto/{config,data,log}
mkdir -p logs

# Start services for the first time
docker compose up -d
```

### 1.5: (Optional) Create Systemd Service for Auto-Start

If you want Docker Compose to start on boot:

```bash
sudo nano /etc/systemd/system/corvids-nest.service
```

Paste this content:

```ini
[Unit]
Description=Corvids Nest Home Automation
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/corvids-nest/server
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=justin
Group=justin

[Install]
WantedBy=multi-user.target
```

Enable and test:

```bash
sudo systemctl enable corvids-nest
sudo systemctl start corvids-nest
sudo systemctl status corvids-nest
```

## Step 2: Configure Your Windows Desktop

### 2.1: Add Git Remote

On your Windows machine, in PowerShell:

```powershell
cd C:\Users\justi\Code\corvids-nest

# Add the server as a Git remote (replace <server-ip> with your Tailscale IP)
git remote add production justin@<server-ip>:/opt/corvids-nest/.git

# Verify
git remote -v
```

### 2.2: Set Up SSH Key (if not already done)

If you don't have an SSH key:

```powershell
# Generate SSH key
ssh-keygen -t ed25519 -C "justin@desktop"

# Copy public key to server
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh justin@<server-ip> "cat >> ~/.ssh/authorized_keys"
```

## Step 3: Deploy!

### Option 1: Use PowerShell Deployment Script

I've created a deployment script for you. Just run:

```powershell
cd C:\Users\justi\Code\corvids-nest
.\deployment\server\deploy.ps1
```

### Option 2: Manual Git Push

```powershell
cd C:\Users\justi\Code\corvids-nest

# Commit your changes
git add .
git commit -m "Your commit message"

# Push to server
git push production main
```

The post-receive hook will automatically:
1. Update the code on the server
2. Rebuild the Docker containers
3. Restart all services

## Step 4: Verify Deployment

SSH into the server and check:

```bash
# Check Docker containers
cd /opt/corvids-nest/server
docker compose ps

# Check logs
docker compose logs -f api

# Check API health
curl http://localhost:8000/health
```

## Common Commands

### On Server (via SSH)

```bash
# View logs
cd /opt/corvids-nest/server
docker compose logs -f

# Restart services
docker compose restart

# Stop services
docker compose down

# Start services
docker compose up -d

# Rebuild and restart
docker compose up -d --build

# Check status
docker compose ps
```

### On Desktop (PowerShell)

```powershell
# Quick deploy
.\deployment\server\deploy.ps1

# Deploy with custom message
.\deployment\server\deploy.ps1 -CommitMessage "Fixed bug in API"

# Deploy without committing (push existing commits)
.\deployment\server\deploy.ps1 -SkipCommit

# View server logs remotely
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose logs -f api"
```

## Troubleshooting

### "Permission denied" when pushing

Make sure your SSH key is added to the server:
```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh justin@<server-ip> "cat >> ~/.ssh/authorized_keys"
```

### Docker containers not starting

Check logs:
```bash
cd /opt/corvids-nest/server
docker compose logs
```

### Changes not reflected after deployment

The post-receive hook rebuilds containers. If changes still don't appear:
```bash
cd /opt/corvids-nest/server
docker compose down
docker compose up -d --build --force-recreate
```

### Want to see what's on the server before pushing?

```powershell
ssh justin@<server-ip> "cd /opt/corvids-nest && git log -5 --oneline"
```

## Development Workflow

For rapid development without committing to Git:

```bash
# On server, directly edit and restart
ssh justin@<server-ip>
cd /opt/corvids-nest/server
nano api/main.py  # or whatever file
docker compose restart api
```

Or use rsync for fast sync during development:

```powershell
# From Windows (in PowerShell)
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' `
  C:\Users\justi\Code\corvids-nest\server\ `
  justin@<server-ip>:/opt/corvids-nest/server/

# Then restart remotely
ssh justin@<server-ip> "cd /opt/corvids-nest/server && docker compose restart api"
```

## Security Notes

1. **Never commit `.env` files** - they contain passwords
2. **Use strong passwords** in production `.env`
3. **Tailscale handles encryption** - no need to expose ports
4. **Keep Docker images updated**: `docker compose pull && docker compose up -d`
5. **Regular backups** of PostgreSQL data volume

## Next Steps

1. Set up database backups
2. Configure log rotation
3. Set up monitoring/alerting
4. Consider adding staging environment for testing
