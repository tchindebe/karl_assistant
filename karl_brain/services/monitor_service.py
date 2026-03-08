"""
Service de monitoring proactif en tâche de fond.
Vérifie périodiquement les métriques et déclenche des alertes automatiques.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.config import get_settings
from services.notification_service import send_notification

logger = logging.getLogger("karl.monitor")
settings = get_settings()

# ── État interne du monitor ────────────────────────────────────────────────────
_last_alert: Dict[str, datetime] = {}       # évite le spam d'alertes
_ALERT_COOLDOWN_MINUTES = 30                # délai minimum entre deux alertes identiques

# Seuils d'alerte (configurables via .env)
THRESHOLDS = {
    "cpu_warning": settings.alert_cpu_warning,        # défaut 80
    "cpu_critical": settings.alert_cpu_critical,      # défaut 95
    "ram_warning": settings.alert_ram_warning,        # défaut 85
    "ram_critical": settings.alert_ram_critical,      # défaut 95
    "disk_warning": settings.alert_disk_warning,      # défaut 80
    "disk_critical": settings.alert_disk_critical,    # défaut 90
}


def _can_alert(key: str, cooldown_minutes: int = _ALERT_COOLDOWN_MINUTES) -> bool:
    """Vérifie si une alerte peut être envoyée (cooldown)."""
    last = _last_alert.get(key)
    if last is None or (datetime.now() - last) > timedelta(minutes=cooldown_minutes):
        _last_alert[key] = datetime.now()
        return True
    return False


async def _check_metrics() -> None:
    """Vérifie les métriques du serveur et alerte si nécessaire."""
    try:
        import httpx
        async with httpx.AsyncClient(
            base_url=settings.vps_agent_url,
            headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
            timeout=10,
        ) as client:
            resp = await client.get("/metrics")
            if resp.status_code != 200:
                return
            metrics = resp.json()

        cpu = metrics.get("cpu_percent", 0)
        ram = metrics.get("ram", {}).get("percent", 0)
        disk = metrics.get("disk", {}).get("percent", 0)

        # ── CPU ──────────────────────────────────────────────────────────────
        if cpu >= THRESHOLDS["cpu_critical"] and _can_alert("cpu_critical"):
            await send_notification(
                f"CPU à **{cpu:.1f}%** — seuil critique atteint.\n"
                f"Processus principaux: {_format_procs(metrics.get('top_processes', []))}",
                title="CPU critique",
                level="critical",
            )
        elif cpu >= THRESHOLDS["cpu_warning"] and _can_alert("cpu_warning"):
            await send_notification(
                f"CPU à **{cpu:.1f}%** depuis quelques minutes.",
                title="CPU élevé",
                level="warning",
            )

        # ── RAM ──────────────────────────────────────────────────────────────
        ram_used_gb = metrics.get("ram", {}).get("used_gb", 0)
        ram_total_gb = metrics.get("ram", {}).get("total_gb", 0)
        if ram >= THRESHOLDS["ram_critical"] and _can_alert("ram_critical"):
            await send_notification(
                f"RAM à **{ram:.1f}%** ({ram_used_gb:.1f}/{ram_total_gb:.1f} GB) — critique.\n"
                f"Processus principaux: {_format_procs(metrics.get('top_processes', []))}",
                title="RAM critique",
                level="critical",
            )
        elif ram >= THRESHOLDS["ram_warning"] and _can_alert("ram_warning"):
            await send_notification(
                f"RAM à **{ram:.1f}%** ({ram_used_gb:.1f}/{ram_total_gb:.1f} GB).",
                title="RAM élevée",
                level="warning",
            )

        # ── Disque ───────────────────────────────────────────────────────────
        disk_used_gb = metrics.get("disk", {}).get("used_gb", 0)
        disk_total_gb = metrics.get("disk", {}).get("total_gb", 0)
        if disk >= THRESHOLDS["disk_critical"] and _can_alert("disk_critical"):
            await send_notification(
                f"Disque à **{disk:.1f}%** ({disk_used_gb:.0f}/{disk_total_gb:.0f} GB) — critique !\n"
                "Risque de saturation imminente.",
                title="Disque critique",
                level="critical",
            )
        elif disk >= THRESHOLDS["disk_warning"] and _can_alert("disk_warning"):
            await send_notification(
                f"Disque à **{disk:.1f}%** ({disk_used_gb:.0f}/{disk_total_gb:.0f} GB).",
                title="Disque presque plein",
                level="warning",
            )

    except Exception as e:
        logger.warning(f"Monitor metrics check failed: {e}")


async def _check_containers() -> None:
    """Vérifie l'état des conteneurs Docker."""
    try:
        import httpx
        async with httpx.AsyncClient(
            base_url=settings.vps_agent_url,
            headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
            timeout=15,
        ) as client:
            resp = await client.get("/deployments")
            if resp.status_code != 200:
                return
            deployments = resp.json()

        for dep in deployments:
            name = dep.get("name", "unknown")
            status = dep.get("status", "").lower()

            if "exit" in status or "error" in status or "dead" in status:
                alert_key = f"container_down_{name}"
                if _can_alert(alert_key, cooldown_minutes=15):
                    await send_notification(
                        f"Le conteneur **{name}** est en état `{status}`.\n"
                        "Karl va tenter un redémarrage automatique.",
                        title=f"Conteneur {name} down",
                        level="critical",
                    )

    except Exception as e:
        logger.warning(f"Monitor containers check failed: {e}")


async def _send_daily_report() -> None:
    """Envoie un rapport quotidien des métriques."""
    try:
        import httpx
        async with httpx.AsyncClient(
            base_url=settings.vps_agent_url,
            headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
            timeout=15,
        ) as client:
            metrics_resp = await client.get("/metrics")
            deploy_resp = await client.get("/deployments")

        if metrics_resp.status_code != 200:
            return

        m = metrics_resp.json()
        deploys = deploy_resp.json() if deploy_resp.status_code == 200 else []
        running = sum(1 for d in deploys if "up" in d.get("status", "").lower())

        report = (
            f"**Rapport quotidien Karl — {datetime.now().strftime('%d/%m/%Y')}**\n\n"
            f"📊 **Métriques actuelles**\n"
            f"• CPU: {m.get('cpu_percent', 0):.1f}%\n"
            f"• RAM: {m.get('ram', {}).get('percent', 0):.1f}% "
            f"({m.get('ram', {}).get('used_gb', 0):.1f}/{m.get('ram', {}).get('total_gb', 0):.1f} GB)\n"
            f"• Disque: {m.get('disk', {}).get('percent', 0):.1f}% "
            f"({m.get('disk', {}).get('used_gb', 0):.0f}/{m.get('disk', {}).get('total_gb', 0):.0f} GB)\n"
            f"• Uptime: {m.get('uptime', 'N/A')}\n\n"
            f"🐳 **Applications**: {running}/{len(deploys)} actives\n"
        )

        await send_notification(report, title="Rapport quotidien", level="info")

    except Exception as e:
        logger.warning(f"Daily report failed: {e}")


def _format_procs(procs: list) -> str:
    if not procs:
        return "N/A"
    return ", ".join(
        f"{p.get('name','?')} ({p.get('cpu_percent',0):.1f}% CPU)"
        for p in procs[:3]
    )


async def run_monitor_loop() -> None:
    """
    Boucle principale du monitor — tourne en arrière-plan.
    Doit être lancée comme tâche asyncio dans le lifespan FastAPI.
    """
    logger.info("Monitor service started")
    check_count = 0
    daily_report_hour = settings.daily_report_hour  # défaut: 8 (8h du matin)
    last_report_day: Optional[int] = None

    while True:
        try:
            await _check_metrics()
            check_count += 1

            # Vérification conteneurs toutes les 5 itérations (selon MONITOR_INTERVAL)
            if check_count % 5 == 0:
                await _check_containers()

            # Rapport quotidien
            now = datetime.now()
            if (
                now.hour == daily_report_hour
                and now.day != last_report_day
                and settings.daily_report_enabled
            ):
                await _send_daily_report()
                last_report_day = now.day

        except Exception as e:
            logger.error(f"Monitor loop error: {e}")

        await asyncio.sleep(settings.monitor_interval_seconds)  # défaut: 60s
