"""
Analyse intelligente des logs via le LLM.
Karl récupère les logs et les analyse pour détecter anomalies, erreurs, patterns.
"""
import httpx
from typing import Any, Dict, Optional
from core.config import get_settings

settings = get_settings()


def _agent() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.vps_agent_url,
        headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
        timeout=30,
    )


async def tool_analyze_logs(
    service: str,
    lines: int = 500,
    since: Optional[str] = None,
    focus: str = "errors",
) -> Dict[str, Any]:
    """
    Récupère les logs d'un service et retourne les données brutes pour analyse.
    Le LLM (Karl) se chargera de l'interprétation intelligente.
    focus: errors | performance | security | all
    """
    async with _agent() as client:
        params = {"lines": lines}
        if since:
            params["since"] = since
        resp = await client.get(f"/logs/{service}", params=params)
        if resp.status_code != 200:
            return {"error": f"Impossible de récupérer les logs: {resp.text}"}
        log_data = resp.json()

    raw_logs = log_data.get("logs", "")
    lines_list = raw_logs.splitlines() if raw_logs else []

    # Pré-analyse côté client (patterns rapides)
    error_lines = [l for l in lines_list if any(k in l.lower() for k in ["error", "err ", "fatal", "exception", "critical"])]
    warning_lines = [l for l in lines_list if any(k in l.lower() for k in ["warn", "warning", "deprecated"])]
    oom_lines = [l for l in lines_list if "out of memory" in l.lower() or "oom" in l.lower()]
    timeout_lines = [l for l in lines_list if "timeout" in l.lower() or "timed out" in l.lower()]

    return {
        "service": service,
        "total_lines": len(lines_list),
        "raw_logs": raw_logs[:8000] if len(raw_logs) > 8000 else raw_logs,
        "truncated": len(raw_logs) > 8000,
        "stats": {
            "errors": len(error_lines),
            "warnings": len(warning_lines),
            "oom_events": len(oom_lines),
            "timeouts": len(timeout_lines),
        },
        "sample_errors": error_lines[:20],
        "sample_warnings": warning_lines[:10],
        "focus": focus,
        "instruction": (
            f"Analyse ces logs du service '{service}'. "
            f"Focus: {focus}. "
            "Identifie les anomalies, patterns récurrents, causes probables et propose des solutions concrètes."
        ),
    }


async def tool_compare_logs(
    service: str,
    period1_since: str,
    period2_since: str,
    lines: int = 200,
) -> Dict[str, Any]:
    """
    Compare les logs sur deux périodes pour identifier des régressions.
    Utile pour diagnostiquer 'pourquoi ça marche moins bien depuis hier'.
    """
    async with _agent() as client:
        resp1 = await client.get(f"/logs/{service}", params={"lines": lines, "since": period1_since})
        resp2 = await client.get(f"/logs/{service}", params={"lines": lines, "since": period2_since})

    logs1 = resp1.json().get("logs", "") if resp1.status_code == 200 else ""
    logs2 = resp2.json().get("logs", "") if resp2.status_code == 200 else ""

    def count_patterns(logs: str) -> Dict[str, int]:
        lines_l = logs.splitlines()
        return {
            "errors": sum(1 for l in lines_l if "error" in l.lower()),
            "warnings": sum(1 for l in lines_l if "warn" in l.lower()),
            "total_lines": len(lines_l),
        }

    return {
        "service": service,
        "period1": {"since": period1_since, "stats": count_patterns(logs1), "sample": logs1[:3000]},
        "period2": {"since": period2_since, "stats": count_patterns(logs2), "sample": logs2[:3000]},
        "instruction": "Compare ces deux périodes de logs et identifie ce qui a changé ou s'est dégradé.",
    }


async def tool_search_logs(
    service: str,
    pattern: str,
    lines: int = 1000,
) -> Dict[str, Any]:
    """Recherche un pattern spécifique dans les logs d'un service."""
    async with _agent() as client:
        resp = await client.get(f"/logs/{service}", params={"lines": lines})
        if resp.status_code != 200:
            return {"error": resp.text}
        log_data = resp.json()

    raw = log_data.get("logs", "")
    matches = [l for l in raw.splitlines() if pattern.lower() in l.lower()]

    return {
        "service": service,
        "pattern": pattern,
        "matches_count": len(matches),
        "matches": matches[:50],
        "searched_lines": lines,
    }
