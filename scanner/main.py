import time
import threading
import logging
import yaml
import os
import sys

from scanner.wifi import scan_wifi, find_target_ssid
from scanner.db import log_scan, log_alert, get_stats
from scanner.alerts import send_alerts
from scanner.web import create_app

logger = logging.getLogger("utr-scanner")

# Shared state for the web dashboard
scanner_state = {
    "status": "starting",
    "last_scan_time": None,
    "last_security": None,
    "consecutive_alerts": 0,
}


def load_config():
    config_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"),
        "/etc/utr-scanner/config.yaml",
    ]
    for path in config_paths:
        if os.path.exists(path):
            with open(path) as f:
                config = yaml.safe_load(f)
            logger.info("Loaded config from %s", path)
            return config

    logger.error("No config.yaml found. Copy config.yaml and edit it.")
    sys.exit(1)


def is_security_ok(actual, expected):
    """Check if the actual security meets the expected level."""
    if not actual or actual == "Open":
        return False
    if actual == "WEP":
        return False

    # Normalize for comparison
    actual_upper = actual.upper().replace(" ", "")
    expected_upper = expected.upper().replace(" ", "")

    # WPA2/WPA3 satisfies WPA2 or WPA3
    if "WPA2" in actual_upper and "WPA2" in expected_upper:
        return True
    if "WPA3" in actual_upper and "WPA3" in expected_upper:
        return True
    # Exact match fallback
    return actual_upper == expected_upper


def scan_loop(config):
    """Main scanning loop - runs in a background thread."""
    interface = config.get("wifi_interface", "wlan0")
    target = config["target_ssid"]
    expected = config["expected_security"]
    interval = config.get("scan_interval", 60)

    logger.info(
        "Starting scan loop: SSID=%s, expected=%s, interface=%s, interval=%ds",
        target, expected, interface, interval,
    )
    scanner_state["status"] = "running"

    while True:
        try:
            networks = scan_wifi(interface)
            result = find_target_ssid(networks, target)

            if result is None:
                scanner_state["status"] = "scanning"
                scanner_state["last_scan_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                scanner_state["last_security"] = "Not found"
                log_scan(target, "Not found", is_alert=False)
                logger.debug("SSID '%s' not found in scan (%d networks seen)", target, len(networks))
            else:
                actual_security = result["security"]
                alert = not is_security_ok(actual_security, expected)

                log_scan(
                    target,
                    actual_security,
                    signal_dbm=result.get("signal_dbm"),
                    frequency=result.get("frequency"),
                    is_alert=alert,
                )

                scanner_state["last_scan_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                scanner_state["last_security"] = actual_security

                if alert:
                    scanner_state["status"] = "alert"
                    scanner_state["consecutive_alerts"] += 1
                    log_alert(target, expected, actual_security)
                    send_alerts(config, target, expected, actual_security)
                    logger.warning(
                        "ALERT: %s is %s (expected %s) - consecutive: %d",
                        target, actual_security, expected, scanner_state["consecutive_alerts"],
                    )
                else:
                    scanner_state["status"] = "ok"
                    scanner_state["consecutive_alerts"] = 0
                    logger.info("OK: %s is %s (signal: %s dBm)", target, actual_security, result.get("signal_dbm"))

        except Exception as e:
            logger.error("Scan loop error: %s", e)
            scanner_state["status"] = "error"

        time.sleep(interval)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "utr-scanner.log")
            ),
        ],
    )

    # Ensure data directory exists
    os.makedirs(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
        exist_ok=True,
    )

    config = load_config()

    # Start scanner in background thread
    scanner_thread = threading.Thread(target=scan_loop, args=(config,), daemon=True)
    scanner_thread.start()

    # Start web server in the main thread
    web_config = config.get("web", {})
    app = create_app(config, scanner_state)
    app.run(
        host=web_config.get("host", "0.0.0.0"),
        port=web_config.get("port", 8585),
        debug=False,
    )


if __name__ == "__main__":
    main()
