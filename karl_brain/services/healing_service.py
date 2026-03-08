"""
Service d'auto-healing — répare automatiquement les problèmes détectés.
Tourne en arrière-plan, surveille et agit sans intervention humaine.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set

import httpx

from core.config import get_settings
from services.notification_service import send_notification

logger = logging.getLogger("karl.healing")
settings = get_settings()

# Garde en mémoire les conteneurs déjà redémarrés (évite les boucles)
_restart_history: Dict[str, list] = {}
_MAX_RESTARTS_PER_HOUR = 3
_healed_today: Set[str] = set()


def _agent_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.vps_agent_url,
        headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
        timeout=30,
    )


def _count_recent_restarts(container: str, window_minutes: int = 60) -> int:
    history = _restart_history.get(container, [])
    cutoff = datetime.now() - timedelta(minutes=window_minutes)
    return sum(1 for ts in history if ts > cutoff)


def _record_restart(container: str) -> None:
    if container not in _restart_history:
        _restart_history[container] = []
    _restart_history[container].append(datetime.now())
    # Nettoyer les anciennes entrées
    cutoff = datetime.now() - timedelta(hours=2)
    _restart_history[container] = [ts for ts in _restart_history[container] if ts > cutoff]


async def _heal_containers() -> None:
    """Détecte et redémarre les conteneurs en échec."""
    try:
        async with _agent_client() as client:
            resp = await client.get("/deployments")
            if resp.status_code != 200:
                return
            deployments = resp.json()

        for dep in deployments:
            name = dep.get("name", "")
            status = dep.get("status", "").lower()

            if not name:
                continue

            needs_restart = any(s in status for s in ["exit", "dead", "error", "oom"])

            if needs_restart:
                recent = _count_recent_restarts(name)

                if recent >= _MAX_RESTARTS_PER_HOUR:
                    if name not in _healed_today:
                        _healed_today.add(name)
                        await send_notification(
                            f"Le conteneur **{name}** a été redémarré {recent} fois en 1h "
                            f"et reste en erreur (`{status}`).\n"
                            "Intervention manuelle requise.",
                            title=f"Healing impossible — {name}",
                            level="critical",
                        )
                    continue

                logger.info(f"Auto-healing: restarting {name} (status={status})")
                async with _agent_client() as client:
                    restart_resp = await client.post(f"/containers/{name}/restart")
                    success = restart_resp.status_code == 200

                _record_restart(name)

                await send_notification(
                    f"Conteneur **{name}** redémarré automatiquement.\n"
                    f"Statut précédent: `{status}`\n"
                    f"Redémarrages récents (1h): {recent + 1}/{_MAX_RESTARTS_PER_HOUR}",
                    title=f"Auto-healing — {name}",
                    level="warning" if success else "critical",
                )

    except Exception as e:
        logger.warning(f"Healing containers check failed: {e}")


async def _heal_disk_space() -> None:
    """Libère de l'espace disque si critique."""
    try:
        async with _agent_client() as client:
            resp = await client.get("/metrics")
            if resp.status_code != 200:
                return
            m = resp.json()

        disk_pct = m.get("disk", {}).get("percent", 0)

        if disk_pct >= settings.alert_disk_critical:
            logger.info(f"Auto-healing: disk at {disk_pct}%, cleaning Docker")

            # Nettoyage Docker (images, volumes, réseaux non utilisés)
            import asyncio
            proc = await asyncio.create_subprocess_exec(
                "docker", "system", "prune", "-f",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            freed = stdout.decode()

            await send_notification(
                f"Disque à **{disk_pct:.1f}%** — nettoyage Docker automatique effectué.\n"
                f"Résultat: {freed[:500]}",
                title="Auto-healing — Disque libéré",
                level="warning",
            )

    except Exception as e:
        logger.warning(f"Healing disk check failed: {e}")


async def _heal_nginx() -> None:
    """Vérifie et relance Nginx s'il est down."""
    try:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "is-active", "nginx",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        status = stdout.decode().strip()

        if status != "active":
            logger.warning("Auto-healing: Nginx is down, restarting")
            restart_proc = await asyncio.create_subprocess_exec(
                "systemctl", "restart", "nginx",
            )
            await restart_proc.communicate()

            await send_notification(
                "Nginx était inactif et a été redémarré automatiquement.",
                title="Auto-healing — Nginx relancé",
                level="warning",
            )
    except Exception:
        pass  # Non critique si systemctl non disponible (dev local)


async def run_healing_loop() -> None:
    """Boucle principale d'auto-healing."""
    logger.info("Auto-healing service started")
    iteration = 0

    while True:
        try:
            await _heal_containers()
            iteration += 1

            # Vérifications moins fréquentes
            if iteration % 5 == 0:
                await _heal_disk_space()
            if iteration % 10 == 0:
                await _heal_nginx()
                _healed_today.clear()  # Reset des notifications

        except Exception as e:
            logger.error(f"Healing loop error: {e}")

        await asyncio.sleep(settings.healing_interval_seconds)  # défaut: 30s
