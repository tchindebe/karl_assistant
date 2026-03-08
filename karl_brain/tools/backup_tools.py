"""
Outils de sauvegarde — Karl peut déclencher, lister et restaurer des sauvegardes.
"""
import httpx
from typing import Any, Dict, Optional
from core.config import get_settings

settings = get_settings()


def _agent() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.vps_agent_url,
        headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
        timeout=600,
    )


async def tool_backup_create(
    backup_type: str = "all",
    app_name: Optional[str] = None,
    db_type: Optional[str] = None,
    container_name: Optional[str] = None,
    database_name: Optional[str] = None,
    db_user: Optional[str] = None,
    db_password: Optional[str] = None,
    upload_s3: bool = False,
    s3_bucket: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée une sauvegarde.
    backup_type: all | volumes | database | configs
    """
    payload = {
        "type": backup_type,
        "app_name": app_name,
        "db_type": db_type,
        "container_name": container_name,
        "database_name": database_name,
        "db_user": db_user,
        "db_password": db_password,
        "upload_s3": upload_s3,
        "s3_bucket": s3_bucket,
    }
    async with _agent() as client:
        resp = await client.post("/backup", json={k: v for k, v in payload.items() if v is not None})
        return resp.json() if resp.status_code == 200 else {"error": resp.text}


async def tool_backup_list(backup_type: str = "all") -> Dict[str, Any]:
    """Liste toutes les sauvegardes disponibles."""
    async with _agent() as client:
        resp = await client.get("/backups", params={"type": backup_type})
        backups = resp.json() if resp.status_code == 200 else []
    return {"backups": backups, "count": len(backups)}


async def tool_backup_restore(backup_file: str, volume_name: str) -> Dict[str, Any]:
    """Restaure un volume depuis une sauvegarde."""
    async with _agent() as client:
        resp = await client.post("/backup/restore", json={
            "backup_file": backup_file,
            "volume_name": volume_name,
        })
        return resp.json() if resp.status_code == 200 else {"error": resp.text}


async def tool_backup_cleanup(keep_days: int = 14) -> Dict[str, Any]:
    """Supprime les sauvegardes plus anciennes que keep_days jours."""
    async with _agent() as client:
        resp = await client.delete("/backups/cleanup", params={"keep_days": keep_days})
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
