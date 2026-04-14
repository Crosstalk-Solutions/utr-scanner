import shutil
import subprocess
import re
import logging

logger = logging.getLogger("utr-scanner")


def _find_iw():
    """Find the iw binary, checking common sbin paths."""
    path = shutil.which("iw")
    if path:
        return path
    for candidate in ("/usr/sbin/iw", "/sbin/iw"):
        try:
            result = subprocess.run(
                [candidate, "--version"], capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "iw"


IW = _find_iw()


def _ensure_interface_up(interface):
    """Bring the WiFi interface up if it's down."""
    try:
        result = subprocess.run(
            ["ip", "link", "show", interface],
            capture_output=True, text=True, timeout=5,
        )
        if "state DOWN" in result.stdout or "state UNKNOWN" in result.stdout:
            logger.info("Bringing %s up", interface)
            subprocess.run(
                ["sudo", "ip", "link", "set", interface, "up"],
                capture_output=True, timeout=10,
            )
    except Exception as e:
        logger.warning("Could not check/bring up %s: %s", interface, e)


def scan_wifi(interface="wlan0"):
    """Scan for nearby WiFi networks using iw.

    Returns a list of dicts with keys: ssid, security, signal_dbm, frequency
    """
    networks = []

    try:
        _ensure_interface_up(interface)

        # Trigger a fresh scan
        subprocess.run(
            ["sudo", IW, "dev", interface, "scan", "trigger"],
            capture_output=True, timeout=10,
        )

        result = subprocess.run(
            ["sudo", IW, "dev", interface, "scan", "dump"],
            capture_output=True, text=True, timeout=30,
        )

        if result.returncode != 0:
            # Fallback: try a blocking scan
            result = subprocess.run(
                ["sudo", IW, "dev", interface, "scan"],
                capture_output=True, text=True, timeout=30,
            )

        if result.returncode != 0:
            logger.error("iw scan failed: %s", result.stderr.strip())
            return networks

        networks = _parse_iw_output(result.stdout)

    except subprocess.TimeoutExpired:
        logger.error("WiFi scan timed out")
    except FileNotFoundError:
        logger.error("iw command not found - install with: sudo apt install iw")
    except Exception as e:
        logger.error("WiFi scan error: %s", e)

    return networks


def _parse_iw_output(output):
    """Parse iw scan output into a list of network dicts."""
    networks = []
    current = None

    for line in output.splitlines():
        line = line.strip()

        # New BSS (access point) entry
        if line.startswith("BSS "):
            if current:
                current["security"] = _determine_security(current)
                networks.append(current)
            current = {
                "ssid": "",
                "signal_dbm": None,
                "frequency": None,
                "security": "Open",
                "_wpa": False,
                "_wpa2": False,
                "_wpa3": False,
                "_rsn": False,
                "_wep": False,
            }

        if not current:
            continue

        if line.startswith("SSID:"):
            current["ssid"] = line.split(":", 1)[1].strip()
        elif line.startswith("signal:"):
            match = re.search(r"(-?\d+\.?\d*)\s*dBm", line)
            if match:
                current["signal_dbm"] = int(float(match.group(1)))
        elif line.startswith("freq:"):
            current["frequency"] = line.split(":", 1)[1].strip()
        elif "WPA:" in line:
            current["_wpa"] = True
        elif "RSN:" in line:
            current["_rsn"] = True
        elif "WEP" in line:
            current["_wep"] = True
        elif "SAE" in line or "802.11w" in line:
            current["_wpa3"] = True

    # Don't forget the last entry
    if current:
        current["security"] = _determine_security(current)
        networks.append(current)

    # Clean up internal keys
    for net in networks:
        for key in ("_wpa", "_wpa2", "_wpa3", "_rsn", "_wep"):
            net.pop(key, None)

    return networks


def _determine_security(net):
    """Determine the security type from parsed flags."""
    if net.get("_wpa3") or (net.get("_rsn") and net.get("_wpa3")):
        if net.get("_rsn"):
            return "WPA2/WPA3"
        return "WPA3"
    if net.get("_rsn") and net.get("_wpa"):
        return "WPA/WPA2"
    if net.get("_rsn"):
        return "WPA2"
    if net.get("_wpa"):
        return "WPA"
    if net.get("_wep"):
        return "WEP"
    return "Open"


def find_target_ssid(networks, target_ssid):
    """Find a specific SSID in the scan results.

    Returns the network dict or None if not found.
    If multiple APs broadcast the same SSID, return the one with the strongest signal.
    """
    matches = [n for n in networks if n["ssid"] == target_ssid]
    if not matches:
        return None
    return max(matches, key=lambda n: n.get("signal_dbm") or -100)
