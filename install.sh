#!/usr/bin/env bash
set -euo pipefail

# UTR Scanner Installer for Raspberry Pi
# Usage: curl -sSL https://raw.githubusercontent.com/Crosstalk-Solutions/utr-scanner/main/install.sh | bash

APP_DIR="/opt/utr-scanner"
SERVICE_NAME="utr-scanner"
REPO="https://github.com/Crosstalk-Solutions/utr-scanner.git"

echo "==============================="
echo "  UTR Scanner Installer"
echo "  WiFi Security Monitor"
echo "==============================="
echo ""

# Check we're on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "Error: This installer is designed for Raspberry Pi / Linux."
    exit 1
fi

# Check for sudo
if [[ $EUID -ne 0 ]]; then
    echo "This installer needs sudo. Re-running with sudo..."
    exec sudo bash "$0" "$@"
fi

echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv iw wireless-tools rfkill git > /dev/null

echo "[2/6] Setting up UTR Scanner..."
if [[ -d "$APP_DIR" ]] && [[ -d "$APP_DIR/.git" ]]; then
    echo "  Existing git installation found, updating..."
    cd "$APP_DIR"
    git pull --quiet
elif [[ -d "$APP_DIR" ]] && [[ -f "$APP_DIR/requirements.txt" ]]; then
    echo "  Existing installation found (manual copy), using as-is..."
else
    git clone --quiet "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "[3/6] Setting up Python environment..."
python3 -m venv venv
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt

echo "[4/7] Unblocking WiFi..."
rfkill unblock wifi 2>/dev/null || true

echo "[5/7] Setting up configuration..."
if [[ ! -f /etc/utr-scanner/config.yaml ]]; then
    mkdir -p /etc/utr-scanner
    cp config.yaml /etc/utr-scanner/config.yaml
else
    echo "  Config already exists at /etc/utr-scanner/config.yaml"
fi

echo "[6/7] Creating data directory..."
mkdir -p "$APP_DIR/data"

echo "[7/7] Installing systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << 'UNIT'
[Unit]
Description=UTR Scanner - WiFi Security Monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/utr-scanner
ExecStart=/opt/utr-scanner/venv/bin/python -m scanner.main
Restart=always
RestartSec=10

# Allow WiFi scanning without full root
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}

echo ""
echo "==============================="
echo "  Installation complete!"
echo "==============================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Start the scanner:"
echo "     sudo systemctl start utr-scanner"
echo ""
echo "  2. Open the dashboard and configure your SSID:"
echo "     http://$(hostname -I | awk '{print $1}'):8585"
echo ""
echo "  The web UI will walk you through selecting the"
echo "  network you want to monitor. No need to edit"
echo "  config files manually."
echo ""
echo "The scanner starts automatically on every boot."
echo ""
echo "Useful commands:"
echo "  sudo systemctl status utr-scanner   # Check status"
echo "  sudo systemctl stop utr-scanner     # Stop scanner"
echo "  sudo journalctl -u utr-scanner -f   # View logs"
echo ""
