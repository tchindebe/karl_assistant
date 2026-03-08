"""
Outils d'optimisation des ressources — Karl analyse et optimise
l'utilisation CPU, RAM, disque et réseau du VPS.
"""
from typing import Any, Dict, List, Optional

from tools.vps_tools import _agent_client


async def tool_get_top_processes(limit: int = 10) -> Dict[str, Any]:
    """
    Retourne les processus qui consomment le plus de ressources (CPU + RAM).
    Utile pour identifier les processus problématiques.
    """
    async with _agent_client() as client:
        resp = await client.get("/metrics")
    if resp.status_code != 200:
        return {"success": False, "error": resp.text}

    m = resp.json()
    processes = m.get("top_processes", [])

    # Trier par CPU desc
    by_cpu = sorted(processes, key=lambda p: p.get("cpu_percent", 0), reverse=True)[:limit]
    by_mem = sorted(processes, key=lambda p: p.get("memory_mb", 0), reverse=True)[:limit]

    return {
        "success": True,
        "by_cpu": by_cpu,
        "by_memory": by_mem,
        "total_processes": len(processes),
    }


async def tool_analyze_resources() -> Dict[str, Any]:
    """
    Analyse complète des ressources et fournit des recommandations d'optimisation.
    Vérifie CPU, RAM, disque, swap, réseau et identifie les goulots d'étranglement.
    """
    async with _agent_client() as client:
        metrics_resp = await client.get("/metrics")
        deploy_resp = await client.get("/deployments")

    if metrics_resp.status_code != 200:
        return {"success": False, "error": "Impossible de récupérer les métriques"}

    m = metrics_resp.json()
    deploys = deploy_resp.json() if deploy_resp.status_code == 200 else []

    cpu = m.get("cpu_percent", 0)
    ram = m.get("ram", {})
    disk = m.get("disk", {})
    network = m.get("network", {})

    recommendations = []
    warnings = []

    # Analyse CPU
    if cpu > 80:
        warnings.append(f"CPU élevé: {cpu:.1f}%")
        recommendations.append({
            "area": "CPU",
            "priority": "high",
            "issue": f"Utilisation CPU à {cpu:.1f}%",
            "suggestions": [
                "Identifier les processus gourmands avec top_processes",
                "Envisager un upgrade de vCPU",
                "Vérifier les tâches CRON consommatrices",
                "Activer l'auto-scaling si l'hébergeur le permet",
            ],
        })

    # Analyse RAM
    ram_pct = ram.get("percent", 0)
    ram_used = ram.get("used_gb", 0)
    ram_total = ram.get("total_gb", 0)
    ram_available = ram.get("available_gb", ram_total - ram_used)

    if ram_pct > 85:
        warnings.append(f"RAM critique: {ram_pct:.1f}%")
        recommendations.append({
            "area": "RAM",
            "priority": "high",
            "issue": f"RAM à {ram_pct:.1f}% ({ram_used:.1f}/{ram_total:.1f} GB)",
            "suggestions": [
                "Vérifier les fuites mémoire dans les conteneurs",
                "Configurer memory limits dans docker-compose (mem_limit: 512m)",
                "Activer le swap si pas encore fait",
                "Optimiser la configuration des BDD (shared_buffers PostgreSQL)",
                "Envisager un upgrade de RAM",
            ],
        })

    # Analyse disque
    disk_pct = disk.get("percent", 0)
    disk_used = disk.get("used_gb", 0)
    disk_total = disk.get("total_gb", 0)

    if disk_pct > 75:
        priority = "critical" if disk_pct > 90 else "high"
        warnings.append(f"Disque: {disk_pct:.1f}%")
        recommendations.append({
            "area": "Disk",
            "priority": priority,
            "issue": f"Disque à {disk_pct:.1f}% ({disk_used:.0f}/{disk_total:.0f} GB)",
            "suggestions": [
                "docker system prune -f pour nettoyer images/conteneurs inutiles",
                "Vérifier les logs volumineux: journalctl --disk-usage",
                "Configurer logrotate pour les logs applicatifs",
                "Analyser l'espace: du -sh /var/log/* /opt/karl/deployments/*",
                "Envisager un disque supplémentaire pour les données",
            ],
        })

    # Analyse swap
    swap = m.get("swap", {})
    swap_pct = swap.get("percent", 0) if swap else 0
    if swap_pct > 50:
        warnings.append(f"Swap élevé: {swap_pct:.1f}%")
        recommendations.append({
            "area": "Swap",
            "priority": "medium",
            "issue": f"Swap utilisé à {swap_pct:.1f}% — signe de pression mémoire",
            "suggestions": [
                "Réduire l'utilisation RAM (voir recommandations RAM)",
                "Le swap excessif dégrade les performances de façon significative",
            ],
        })

    # Analyse conteneurs
    running_containers = [d for d in deploys if isinstance(d, dict) and "up" in d.get("status", "").lower()]
    if len(running_containers) > 10:
        recommendations.append({
            "area": "Containers",
            "priority": "low",
            "issue": f"{len(running_containers)} conteneurs en cours d'exécution",
            "suggestions": [
                "Vérifier que tous les conteneurs sont nécessaires",
                "Consolider les services similaires",
                "Appliquer des resource limits sur chaque service",
            ],
        })

    # Score de santé global
    health_score = 100
    for w in warnings:
        health_score -= 15
    health_score = max(0, health_score)

    return {
        "success": True,
        "health_score": health_score,
        "warnings": warnings,
        "recommendations": recommendations,
        "current_metrics": {
            "cpu_percent": cpu,
            "ram_percent": ram_pct,
            "ram_available_gb": ram_available,
            "disk_percent": disk_pct,
            "disk_free_gb": disk_total - disk_used,
            "swap_percent": swap_pct,
            "running_containers": len(running_containers),
        },
    }


async def tool_clean_docker() -> Dict[str, Any]:
    """
    Nettoie les ressources Docker inutilisées:
    images non utilisées, conteneurs arrêtés, volumes orphelins, réseaux inutilisés.
    Libère de l'espace disque sans impacter les apps actives.
    """
    async with _agent_client() as client:
        # Utiliser l'endpoint de nettoyage ou le healing disk
        resp = await client.post("/system/docker-prune")

    if resp.status_code == 200:
        return resp.json()

    # Fallback: endpoint metrics pour vérifier après nettoyage
    return {
        "success": False,
        "error": "Endpoint /system/docker-prune non disponible — utiliser l'auto-healing",
        "hint": "Le service d'auto-healing effectue ce nettoyage automatiquement quand le disque est critique",
    }


async def tool_get_network_stats() -> Dict[str, Any]:
    """
    Retourne les statistiques réseau: bande passante entrant/sortant,
    nombre de connexions actives, top des connexions.
    """
    async with _agent_client() as client:
        resp = await client.get("/metrics")

    if resp.status_code != 200:
        return {"success": False, "error": resp.text}

    m = resp.json()
    network = m.get("network", {})

    return {
        "success": True,
        "network": network,
        "bytes_sent_mb": network.get("bytes_sent", 0) / (1024 * 1024),
        "bytes_recv_mb": network.get("bytes_recv", 0) / (1024 * 1024),
    }


async def tool_get_disk_usage_breakdown() -> Dict[str, Any]:
    """
    Analyse l'utilisation du disque par répertoire pour identifier
    ce qui prend le plus de place.
    """
    async with _agent_client() as client:
        resp = await client.get("/system/disk-breakdown")

    if resp.status_code == 200:
        return resp.json()

    return {
        "success": False,
        "error": "Endpoint non disponible",
        "hint": "Vérifier les métriques de base via tool_get_server_metrics",
    }


async def tool_set_container_limits(
    app_name: str,
    cpu_limit: Optional[str] = None,
    memory_limit: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Applique des limites de ressources à un conteneur via docker update.
    cpu_limit: ex '0.5' (50% d'un CPU) ou '2' (2 CPUs)
    memory_limit: ex '512m', '1g', '2g'
    Note: Modifier le docker-compose.yml est préférable pour la persistance.
    """
    if not cpu_limit and not memory_limit:
        return {"success": False, "error": "Spécifier au moins une limite (cpu_limit ou memory_limit)"}

    async with _agent_client() as client:
        resp = await client.post("/containers/limits", json={
            "app_name": app_name,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
        })

    if resp.status_code == 200:
        return resp.json()

    return {
        "success": False,
        "error": resp.text,
        "hint": (
            f"Ajouter manuellement dans docker-compose.yml pour {app_name}:\n"
            "deploy:\n  resources:\n    limits:\n"
            f"      cpus: '{cpu_limit or '1'}'\n"
            f"      memory: {memory_limit or '512m'}"
        ),
    }
