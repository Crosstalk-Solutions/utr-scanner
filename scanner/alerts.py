import logging
import subprocess

logger = logging.getLogger("utr-scanner")


def send_alerts(config, ssid, expected, actual):
    """Send alerts through all configured channels."""
    alert_config = config.get("alerts", {})

    message = (
        f"SECURITY ALERT: {ssid} is broadcasting as {actual} "
        f"(expected {expected})"
    )
    logger.warning(message)

    if alert_config.get("beep"):
        _beep()

    webhook_url = alert_config.get("webhook_url")
    if webhook_url:
        _send_webhook(webhook_url, ssid, expected, actual)

    pushover = alert_config.get("pushover")
    if pushover:
        _send_pushover(pushover, message)


def _beep():
    """Sound an audible alert on the Pi."""
    try:
        # Try the terminal bell
        print("\a", flush=True)
        # Also try speaker via aplay if available
        subprocess.run(
            ["speaker-test", "-t", "sine", "-f", "1000", "-l", "1", "-p", "1"],
            capture_output=True, timeout=3,
        )
    except Exception:
        pass


def _send_webhook(url, ssid, expected, actual):
    """Send a webhook notification (works with Slack, Discord, etc.)."""
    try:
        import requests

        payload = {
            "text": (
                f":rotating_light: *WiFi Security Alert*\n"
                f"SSID `{ssid}` detected as *{actual}* (expected *{expected}*)\n"
                f"Your network may be exposed!"
            ),
            # Discord-compatible format
            "content": (
                f"**WiFi Security Alert**\n"
                f"SSID `{ssid}` detected as **{actual}** (expected **{expected}**)\n"
                f"Your network may be exposed!"
            ),
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            logger.info("Webhook alert sent")
        else:
            logger.error("Webhook failed: %s", resp.status_code)
    except Exception as e:
        logger.error("Webhook error: %s", e)


def _send_pushover(pushover_config, message):
    """Send a Pushover push notification."""
    try:
        import requests

        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": pushover_config["api_token"],
                "user": pushover_config["user_key"],
                "message": message,
                "title": "UTR Scanner Alert",
                "priority": 1,
                "sound": "siren",
            },
            timeout=10,
        )
        if resp.ok:
            logger.info("Pushover alert sent")
        else:
            logger.error("Pushover failed: %s", resp.status_code)
    except Exception as e:
        logger.error("Pushover error: %s", e)
