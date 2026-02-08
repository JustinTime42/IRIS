#!/bin/bash
# Server-side setup script for Corvids Nest deployment
# Run this on the Linux server to set up the deployment infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
DEPLOY_DIR="/opt/corvids-nest"
SERVER_DIR="${DEPLOY_DIR}/server"
USER=$(whoami)

info "════════════════════════════════════════════"
info "  Corvids Nest Server Deployment Setup"
info "════════════════════════════════════════════"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    error "Don't run this script as root. Run as your regular user."
    error "The script will use sudo when necessary."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    error "Docker is not installed!"
    info "Install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    error "Docker Compose plugin is not installed!"
    info "Install Docker Compose plugin: sudo apt install docker-compose-plugin"
    exit 1
fi

# Create deployment directory
info "Creating deployment directory: ${DEPLOY_DIR}"
sudo mkdir -p "${DEPLOY_DIR}"
sudo chown "${USER}:${USER}" "${DEPLOY_DIR}"
success "Created ${DEPLOY_DIR}"

# Initialize Git repository if not already done
cd "${DEPLOY_DIR}"
if [ ! -d ".git" ]; then
    info "Initializing Git repository..."
    git init
    git config receive.denyCurrentBranch ignore
    success "Git repository initialized"
else
    info "Git repository already exists"
fi

# Create post-receive hook
info "Creating post-receive hook..."
mkdir -p .git/hooks

cat > .git/hooks/post-receive << 'HOOK_EOF'
#!/bin/bash
set -e
unset GIT_DIR

echo "═══════════════════════════════════════════════"
echo "  Starting Corvids Nest Deployment"
echo "═══════════════════════════════════════════════"
echo ""

# Stop services first to release file locks (e.g. mosquitto.conf)
echo "[1/3] Stopping services..."
cd /opt/corvids-nest/server && docker compose down

# Update code — safe now that services are stopped
echo "[2/3] Updating code..."
cd /opt/corvids-nest && git reset --hard HEAD

# Check if .env exists
if [ ! -f server/.env ]; then
    echo "WARNING: server/.env file not found! Please create it before starting services."
    exit 1
fi

# Build and start services
echo "[3/3] Building and starting services..."
cd /opt/corvids-nest/server && docker compose up -d --build

# Wait a moment for services to start
sleep 3

# Check status
docker compose ps

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✓ Deployment Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "View logs: cd /opt/corvids-nest/server && docker compose logs -f"
echo "Check health: curl http://localhost:8000/health"
echo ""
HOOK_EOF

chmod +x .git/hooks/post-receive
success "Post-receive hook created and made executable"

# Create server directories if needed
info "Setting up server directory structure..."
mkdir -p "${SERVER_DIR}/mosquitto/config"
mkdir -p "${SERVER_DIR}/mosquitto/data"
mkdir -p "${SERVER_DIR}/mosquitto/log"
mkdir -p "${SERVER_DIR}/logs"
success "Server directories created"

# Check if .env exists
if [ ! -f "${SERVER_DIR}/.env" ]; then
    warning ".env file not found!"
    info "You'll need to create ${SERVER_DIR}/.env before deploying"
    info "Copy .env.example if you have one, or create from scratch"
    info ""
    info "Required variables:"
    info "  - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB"
    info "  - MQTT_USERNAME, MQTT_PASSWORD"
    info "  - API_SECRET_KEY"
    info "  - PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD"
else
    success ".env file found"
fi

# Create systemd service for auto-start on boot
info "Creating systemd service for auto-start..."

sudo tee /etc/systemd/system/corvids-nest.service > /dev/null << SERVICE_EOF
[Unit]
Description=Corvids Nest Home Automation
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${SERVER_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
User=${USER}
Group=${USER}
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable corvids-nest

success "Systemd service created and enabled"

echo ""
info "════════════════════════════════════════════"
info "  Setup Complete!"
info "════════════════════════════════════════════"
echo ""

info "Next steps:"
echo ""
echo "1. Configure .env file:"
echo "   nano ${SERVER_DIR}/.env"
echo ""
echo "2. On your Windows desktop, add this server as a Git remote:"
echo "   git remote add production ${USER}@<server-ip>:${DEPLOY_DIR}/.git"
echo ""
echo "3. Deploy from Windows:"
echo "   cd C:\\Users\\justi\\Code\\corvids-nest"
echo "   .\\deployment\\server\\deploy.ps1"
echo ""

info "Useful commands:"
echo ""
echo "Start services:   sudo systemctl start corvids-nest"
echo "Stop services:    sudo systemctl stop corvids-nest"
echo "Service status:   sudo systemctl status corvids-nest"
echo ""
echo "Manual control:"
echo "  cd ${SERVER_DIR}"
echo "  docker compose up -d    # Start"
echo "  docker compose down     # Stop"
echo "  docker compose logs -f  # View logs"
echo "  docker compose ps       # Check status"
echo ""

success "Server is ready for deployment! 🚀"
