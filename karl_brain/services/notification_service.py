"""
Service de notifications multi-canal.
Supporte: Email (SMTP), Telegram, Slack, webhook custom.
"""
import smtplib
import json
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime

from core.config import get_settings

settings = get_settings()


async def send_notification(
    message: str,
    title: str = "Karl Alert",
    level: str = "info",   # info | warning | critical
    channels: Optional[List[str]] = None,
) -> dict:
    """
    Envoie une notification sur tous les canaux configurés.
    Retourne le statut d'envoi par canal.
    """
    if channels is None:
        channels = _get_enabled_channels()

    results = {}
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "📢")
    full_message = f"{emoji} *{title}*\n\n{message}\n\n_Karl — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"

    for channel in channels:
        try:
            if channel == "telegram":
                results["telegram"] = await _send_telegram(full_message)
            elif channel == "slack":
                results["slack"] = await _send_slack(title, message, level)
            elif channel == "email":
                results["email"] = await _send_email(title, message, level)
            elif channel == "webhook":
                results["webhook"] = await _send_webhook(title, message, level)
        except Exception as e:
            results[channel] = {"success": False, "error": str(e)}

    return results


def _get_enabled_channels() -> List[str]:
    """Retourne les canaux configurés dans .env."""
    channels = []
    if settings.telegram_bot_token and settings.telegram_chat_id:
        channels.append("telegram")
    if settings.slack_webhook_url:
        channels.append("slack")
    if settings.smtp_host and settings.notification_email_to:
        channels.append("email")
    if settings.notification_webhook_url:
        channels.append("webhook")
    return channels


async def _send_telegram(message: str) -> dict:
    """Envoie un message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json={
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
        resp.raise_for_status()
    return {"success": True, "channel": "telegram"}


async def _send_slack(title: str, message: str, level: str) -> dict:
    """Envoie un message via Slack Incoming Webhook."""
    color = {"info": "#36a64f", "warning": "#ff9900", "critical": "#ff0000"}.get(level, "#36a64f")
    payload = {
        "attachments": [{
            "color": color,
            "title": f"Karl — {title}",
            "text": message,
            "footer": "Karl VPS Assistant",
            "ts": int(datetime.now().timestamp()),
        }]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(settings.slack_webhook_url, json=payload)
        resp.raise_for_status()
    return {"success": True, "channel": "slack"}


async def _send_email(title: str, message: str, level: str) -> dict:
    """Envoie un email via SMTP."""
    import asyncio

    def _smtp_send():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Karl {level.upper()}] {title}"
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = settings.notification_email_to

        # Version texte
        text_part = MIMEText(message, "plain", "utf-8")
        # Version HTML
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:{'#dc3545' if level=='critical' else '#ffc107' if level=='warning' else '#0d6efd'};
                      color:white;padding:16px;border-radius:8px 8px 0 0">
            <h2 style="margin:0">Karl — {title}</h2>
          </div>
          <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px">
            <pre style="white-space:pre-wrap;font-family:monospace">{message}</pre>
            <hr style="border:1px solid #dee2e6">
            <small style="color:#6c757d">Karl VPS Assistant — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
          </div>
        </body></html>
        """
        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(text_part)
        msg.attach(html_part)

        port = settings.smtp_port or 587
        if port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, port)
        else:
            server = smtplib.SMTP(settings.smtp_host, port)
            server.starttls()

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.sendmail(msg["From"], msg["To"], msg.as_string())
        server.quit()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _smtp_send)
    return {"success": True, "channel": "email", "to": settings.notification_email_to}


async def _send_webhook(title: str, message: str, level: str) -> dict:
    """Envoie un payload JSON vers un webhook custom."""
    payload = {
        "source": "karl",
        "level": level,
        "title": title,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(settings.notification_webhook_url, json=payload)
        resp.raise_for_status()
    return {"success": True, "channel": "webhook"}
