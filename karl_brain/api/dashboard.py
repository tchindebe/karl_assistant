"""
Proxy endpoints pour le dashboard frontend.
Transmet les appels de statut vers le VPS Agent pour affichage dans les
panneaux du dashboard React.
"""
from fastapi import APIRouter, Depends

from core.security import get_current_user
from tools.vps_tools import _agent_client

router = APIRouter(prefix="/api", tags=["dashboard"])


async def _vps_get(path: str, params: dict | None = None) -> dict:
    """GET vers le VPS Agent avec fallback d'erreur."""
    try:
        async with _agent_client() as client:
            resp = await client.get(path, params=params or {})
        return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/ssl")
async def ssl_status(_: str = Depends(get_current_user)):
    """Liste les certificats SSL avec statut d'expiration."""
    return await _vps_get("/ssl/expiry")


@router.get("/security/status")
async def security_status(_: str = Depends(get_current_user)):
    """Résumé de l'audit de sécurité (SSH, ports, mises à jour, Docker)."""
    return await _vps_get("/security")


@router.get("/firewall")
async def firewall_status(_: str = Depends(get_current_user)):
    """Statut du pare-feu UFW + règles actives."""
    return await _vps_get("/firewall/status")


@router.get("/backups")
async def backups_list(_: str = Depends(get_current_user)):
    """Liste des sauvegardes disponibles (volumes, BDD, configs)."""
    return await _vps_get("/backups/list")


@router.get("/apps/available")
async def apps_available(_: str = Depends(get_current_user)):
    """Catalogue d'applications disponibles dans l'App Store."""
    return await _vps_get("/apps/list")


@router.get("/containers")
async def containers_list(_: str = Depends(get_current_user)):
    """Liste tous les conteneurs Docker (pour le panneau Databases)."""
    return await _vps_get("/containers")
