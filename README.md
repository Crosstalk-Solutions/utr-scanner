# UTR Scanner - WiFi Security Monitor

A lightweight Raspberry Pi tool that continuously monitors a WiFi SSID's security level and alerts you if it drops from WPA2/WPA3 to an open or insecure state.

## Why?

There's a [reported bug](https://community.ui.com/questions/UniFi-Travel-Router-Unsecure-WiFi/83fa9d26-d929-4623-aba8-90048eb813fe) in the UniFi Travel Router (UTR) where the device periodically broadcasts a configured WPA2 network as an **open, unsecured network** — giving anyone in range direct access to your home network via the Teleport tunnel.

Multiple users have confirmed the issue. It appears intermittent and difficult to reproduce, which makes it even more dangerous. This tool sits on your LAN and watches for exactly this scenario.

## What It Does

- Scans for your target SSID once per minute (configurable)
- Logs the security type (WPA2, WPA3, WEP, Open) with timestamp and signal strength
- Alerts immediately if security drops below expected level
- Provides a clean web dashboard at `http://<pi-ip>:8585`
- Shows a 24-hour security timeline so you can spot intermittent issues
- Supports alerts via webhook (Slack/Discord), Pushover, or audible beep

## Quick Install (Raspberry Pi)

```bash
git clone https://github.com/Crosstalk-Solutions/utr-scanner.git /opt/utr-scanner
cd /opt/utr-scanner
sudo bash install.sh
```

Then:

1. Edit your config:
   ```bash
   sudo nano /etc/utr-scanner/config.yaml
   ```
2. Set your `target_ssid` and `expected_security`
3. Start the scanner:
   ```bash
   sudo systemctl start utr-scanner
   ```
4. Open the dashboard: `http://<your-pi-ip>:8585`

## Configuration

Edit `/etc/utr-scanner/config.yaml`:

```yaml
target_ssid: "MyNetwork"        # The SSID to monitor
expected_security: "WPA2"       # Expected: WPA2, WPA3, WPA2/WPA3
scan_interval: 60               # Seconds between scans
wifi_interface: "wlan0"         # WiFi adapter to use

web:
  host: "0.0.0.0"
  port: 8585

alerts:
  beep: true
  # webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  # pushover:
  #   user_key: "your-user-key"
  #   api_token: "your-api-token"
```

## Requirements

- Raspberry Pi (any model with WiFi)
- Raspberry Pi OS (Bookworm or later recommended)
- Python 3.9+
- A WiFi adapter that can scan (the built-in one works)

**Tip:** If you're using the Pi's WiFi for network connectivity, consider adding a USB WiFi adapter dedicated to scanning. This avoids brief connectivity interruptions during scans.

## Dashboard

The web dashboard shows:

- **Live status** — current security state with a green/red indicator
- **Scan log** — timestamped history of every scan with security type and signal strength
- **24-hour timeline** — visual bar showing security state over time (green = secure, red = insecure, yellow = SSID not found)
- **Active alerts** — dismissable alerts when insecure state is detected

## Managing the Service

```bash
sudo systemctl start utr-scanner    # Start
sudo systemctl stop utr-scanner     # Stop
sudo systemctl restart utr-scanner  # Restart
sudo systemctl status utr-scanner   # Status
sudo journalctl -u utr-scanner -f   # Live logs
```

## Uninstall

```bash
sudo bash /opt/utr-scanner/uninstall.sh
```

## License

MIT
