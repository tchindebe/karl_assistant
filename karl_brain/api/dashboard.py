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
    raw = await _vps_get("/security/audit")
    if raw.get("error"):
        return raw

    results = raw.get("results", {})

    # SSH config (results.ssh_config.config → flat keys)
    ssh_config_raw = results.get("ssh_config", {}).get("config", {})
    ssh_flat = {
        "password_auth": ssh_config_raw.get("PasswordAuthentication", "yes"),
        "permit_root": ssh_config_raw.get("PermitRootLogin", "yes"),
    }

    # Open ports list
    open_ports = results.get("open_ports", {}).get("open_ports", [])

    # System updates
    updates_raw = results.get("system_updates", {})
    system_updates = {
        "available": updates_raw.get("total_upgradable"),
        "security": updates_raw.get("security_updates"),
    }

    # Docker privileged containers (extract container name from issue description)
    docker_issues = results.get("docker_images", {}).get("issues", [])
    privileged = [
        i["description"].split()[1]
        for i in docker_issues
        if i.get("type") == "docker_security" and len(i["description"].split()) > 1
    ]

    # Failed logins
    failed_raw = results.get("failed_logins", {})
    failed_logins = {"count": failed_raw.get("total_failures_24h", 0)}

    # Fail2ban
    fail2ban_raw = results.get("fail2ban", {})
    fail2ban = {
        "installed": fail2ban_raw.get("installed", False),
        "active": fail2ban_raw.get("active", False),
    }

    return {
        "success": True,
        "score": raw.get("security_score"),
        "grade": raw.get("grade"),
        "ssh_config": ssh_flat,
        "open_ports": open_ports,
        "system_updates": system_updates,
        "docker_security": {"privileged_containers": privileged},
        "failed_logins": failed_logins,
        "fail2ban": fail2ban,
    }


@router.get("/firewall")
async def firewall_status(_: str = Depends(get_current_user)):
    """Statut du pare-feu UFW + règles actives."""
    return await _vps_get("/firewall/status")


@router.get("/backups")
async def backups_list(_: str = Depends(get_current_user)):
    """Liste des sauvegardes disponibles (volumes, BDD, configs)."""
    return await _vps_get("/backups")



@router.get("/containers")
async def containers_list(_: str = Depends(get_current_user)):
    """Liste tous les conteneurs Docker (pour le panneau Databases)."""
    return await _vps_get("/containers")
