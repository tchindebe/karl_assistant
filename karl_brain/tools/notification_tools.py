"""
Outils de notification — Karl peut envoyer des alertes manuellement.
"""
from typing import Any, Dict, List, Optional
from services.notification_service import send_notification


async def tool_send_notification(
    message: str,
    title: str = "Karl",
    level: str = "info",
    channels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Envoie une notification sur les canaux configurés.
    level: info | warning | critical
    channels: ["telegram", "slack", "email", "webhook"] ou None pour tous
    """
    results = await send_notification(message, title=title, level=level, channels=channels)
    sent = [ch for ch, r in results.items() if isinstance(r, dict) and r.get("success")]
    failed = [ch for ch, r in results.items() if isinstance(r, dict) and not r.get("success")]

    return {
        "success": len(sent) > 0,
        "sent_via": sent,
        "failed": failed,
        "details": results,
    }


async def tool_get_notification_config() -> Dict[str, Any]:
    """Retourne la configuration des canaux de notification disponibles."""
    from core.config import get_settings
    s = get_settings()
    return {
        "channels": {
            "telegram": bool(s.telegram_bot_token and s.telegram_chat_id),
            "slack": bool(s.slack_webhook_url),
            "email": bool(s.smtp_host and s.notification_email_to),
            "webhook": bool(s.notification_webhook_url),
        },
        "thresholds": {
            "cpu_warning": s.alert_cpu_warning,
            "cpu_critical": s.alert_cpu_critical,
            "ram_warning": s.alert_ram_warning,
            "ram_critical": s.alert_ram_critical,
            "disk_warning": s.alert_disk_warning,
            "disk_critical": s.alert_disk_critical,
        },
        "monitor_interval_seconds": s.monitor_interval_seconds,
        "daily_report_enabled": s.daily_report_enabled,
        "daily_report_hour": s.daily_report_hour,
    }
