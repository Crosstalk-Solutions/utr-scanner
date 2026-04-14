#!/usr/bin/env bash
set -euo pipefail

# UTR Scanner Uninstaller

if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

echo "Stopping UTR Scanner..."
systemctl stop utr-scanner 2>/dev/null || true
systemctl disable utr-scanner 2>/dev/null || true
rm -f /etc/systemd/system/utr-scanner.service
systemctl daemon-reload

echo "Removing application files..."
rm -rf /opt/utr-scanner

echo ""
read -p "Remove config at /etc/utr-scanner/config.yaml? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /etc/utr-scanner
    echo "Config removed."
else
    echo "Config preserved at /etc/utr-scanner/config.yaml"
fi

echo "UTR Scanner uninstalled."
