import yaml
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from scanner.db import get_recent_scans, get_alerts, acknowledge_alert, get_stats
from scanner.wifi import scan_wifi

CONFIG_PATHS = [
    "/etc/utr-scanner/config.yaml",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"),
]


def _get_config_path():
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return CONFIG_PATHS[0]


def _save_config(config):
    path = _get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def create_app(config, scanner_state):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    @app.route("/")
    def index():
        stats = get_stats()
        needs_setup = config.get("target_ssid") in (None, "", "MyNetwork")
        return render_template(
            "index.html",
            config=config,
            state=scanner_state,
            stats=stats,
            needs_setup=needs_setup,
        )

    @app.route("/setup")
    def setup():
        return render_template(
            "setup.html",
            config=config,
        )

    @app.route("/api/scans")
    def api_scans():
        limit = request.args.get("limit", 500, type=int)
        return jsonify(get_recent_scans(limit))

    @app.route("/api/alerts")
    def api_alerts():
        return jsonify(get_alerts(acknowledged=False))

    @app.route("/api/stats")
    def api_stats():
        stats = get_stats()
        stats["scanner_state"] = scanner_state
        return jsonify(stats)

    @app.route("/api/alerts/<int:alert_id>/acknowledge", methods=["POST"])
    def api_acknowledge(alert_id):
        acknowledge_alert(alert_id)
        return jsonify({"ok": True})

    @app.route("/api/scan-networks")
    def api_scan_networks():
        interface = config.get("wifi_interface", "wlan0")
        networks = scan_wifi(interface)
        # Deduplicate by SSID, keeping strongest signal
        seen = {}
        for net in networks:
            ssid = net["ssid"]
            if not ssid or "\\x00" in ssid:
                continue
            if ssid not in seen or (net.get("signal_dbm") or -100) > (seen[ssid].get("signal_dbm") or -100):
                seen[ssid] = net
        unique = sorted(seen.values(), key=lambda n: n.get("signal_dbm") or -100, reverse=True)
        return jsonify(unique)

    @app.route("/api/config", methods=["GET"])
    def api_get_config():
        return jsonify({
            "target_ssid": config.get("target_ssid", ""),
            "expected_security": config.get("expected_security", "WPA2"),
            "scan_interval": config.get("scan_interval", 60),
            "wifi_interface": config.get("wifi_interface", "wlan0"),
        })

    @app.route("/api/config", methods=["POST"])
    def api_save_config():
        data = request.get_json()
        if not data or not data.get("target_ssid"):
            return jsonify({"error": "target_ssid is required"}), 400

        config["target_ssid"] = data["target_ssid"]
        config["expected_security"] = data.get("expected_security", "WPA2")
        if data.get("scan_interval"):
            config["scan_interval"] = int(data["scan_interval"])

        _save_config(config)

        # Reset scanner state so it picks up the new SSID immediately
        scanner_state["status"] = "running"
        scanner_state["last_security"] = None
        scanner_state["consecutive_alerts"] = 0

        return jsonify({"ok": True, "message": "Config saved. Scanner will use new settings on next scan cycle."})

    return app
