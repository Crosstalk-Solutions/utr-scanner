from flask import Flask, render_template, jsonify, request, redirect, url_for
from scanner.db import get_recent_scans, get_alerts, acknowledge_alert, get_stats


def create_app(config, scanner_state):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    @app.route("/")
    def index():
        stats = get_stats()
        return render_template(
            "index.html",
            config=config,
            state=scanner_state,
            stats=stats,
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

    return app
