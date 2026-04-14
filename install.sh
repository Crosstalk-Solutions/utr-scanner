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
apt-get install -y -qq python3 python3-pip python3-venv iw wireless-tools git > /dev/null

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

echo "[4/6] Setting up configuration..."
if [[ ! -f /etc/utr-scanner/config.yaml ]]; then
    mkdir -p /etc/utr-scanner
    cp config.yaml /etc/utr-scanner/config.yaml
    echo ""
    echo "  *** IMPORTANT: Edit your config before starting! ***"
    echo "  sudo nano /etc/utr-scanner/config.yaml"
    echo ""
    echo "  At minimum, set:"
    echo "    target_ssid: \"YourNetworkName\""
    echo "    expected_security: \"WPA2\""
    echo ""
else
    echo "  Config already exists at /etc/utr-scanner/config.yaml"
fi

echo "[5/6] Creating data directory..."
mkdir -p "$APP_DIR/data"

echo "[6/6] Installing systemd service..."
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
echo "  1. Edit your config:"
echo "     sudo nano /etc/utr-scanner/config.yaml"
echo ""
echo "  2. Start the scanner:"
echo "     sudo systemctl start utr-scanner"
echo ""
echo "  3. Open the dashboard:"
echo "     http://$(hostname -I | awk '{print $1}'):8585"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status utr-scanner   # Check status"
echo "  sudo systemctl stop utr-scanner     # Stop scanner"
echo "  sudo journalctl -u utr-scanner -f   # View logs"
echo ""
