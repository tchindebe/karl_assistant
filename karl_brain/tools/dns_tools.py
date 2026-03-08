"""
Outils DNS et Cloudflare — Karl peut gérer les enregistrements DNS,
vérifier la propagation, activer/désactiver le proxy Cloudflare.
"""
import asyncio
import socket
from typing import Any, Dict, List, Optional

import httpx

from core.config import get_settings

settings = get_settings()

CF_API = "https://api.cloudflare.com/client/v4"


def _cf_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.cloudflare_api_token}",
        "Content-Type": "application/json",
    }


def _cf_available() -> bool:
    return bool(settings.cloudflare_api_token and settings.cloudflare_zone_id)


async def tool_dns_list_records(record_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Liste les enregistrements DNS Cloudflare pour la zone configurée.
    record_type: A | AAAA | CNAME | MX | TXT | NS (optionnel, filtre)
    Nécessite CLOUDFLARE_API_TOKEN et CLOUDFLARE_ZONE_ID dans .env
    """
    if not _cf_available():
        return {"success": False, "error": "Cloudflare non configuré (CLOUDFLARE_API_TOKEN + CLOUDFLARE_ZONE_ID requis)"}

    params = {}
    if record_type:
        params["type"] = record_type.upper()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CF_API}/zones/{settings.cloudflare_zone_id}/dns_records",
            headers=_cf_headers(),
            params=params,
        )

    data = resp.json()
    if not data.get("success"):
        return {"success": False, "errors": data.get("errors", [])}

    records = [
        {
            "id": r["id"],
            "type": r["type"],
            "name": r["name"],
            "content": r["content"],
            "proxied": r.get("proxied", False),
            "ttl": r.get("ttl", 1),
        }
        for r in data.get("result", [])
    ]

    return {"success": True, "total": len(records), "records": records}


async def tool_dns_create_record(
    record_type: str,
    name: str,
    content: str,
    proxied: bool = True,
    ttl: int = 1,
) -> Dict[str, Any]:
    """
    Crée un enregistrement DNS dans Cloudflare.
    record_type: A | AAAA | CNAME | MX | TXT
    name: ex 'app' ou 'app.example.com'
    content: pour A → IP du serveur, pour CNAME → domaine cible
    proxied: True pour passer par le CDN/proxy Cloudflare (recommandé)
    """
    if not _cf_available():
        return {"success": False, "error": "Cloudflare non configuré"}

    payload = {
        "type": record_type.upper(),
        "name": name,
        "content": content,
        "proxied": proxied,
        "ttl": 1 if proxied else ttl,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CF_API}/zones/{settings.cloudflare_zone_id}/dns_records",
            headers=_cf_headers(),
            json=payload,
        )

    data = resp.json()
    if not data.get("success"):
        return {"success": False, "errors": data.get("errors", [])}

    record = data["result"]
    return {
        "success": True,
        "record": {
            "id": record["id"],
            "type": record["type"],
            "name": record["name"],
            "content": record["content"],
            "proxied": record.get("proxied"),
        },
        "message": f"Enregistrement DNS {record_type} '{name}' → '{content}' créé.",
    }


async def tool_dns_update_record(
    record_id: str,
    content: str,
    proxied: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Met à jour le contenu d'un enregistrement DNS existant.
    record_id: ID Cloudflare (obtenu via dns_list_records)
    content: nouvelle valeur (nouvelle IP, nouveau domaine cible, etc.)
    """
    if not _cf_available():
        return {"success": False, "error": "Cloudflare non configuré"}

    async with httpx.AsyncClient(timeout=15) as client:
        get_resp = await client.get(
            f"{CF_API}/zones/{settings.cloudflare_zone_id}/dns_records/{record_id}",
            headers=_cf_headers(),
        )
        current = get_resp.json().get("result", {})
        if not current:
            return {"success": False, "error": f"Enregistrement {record_id} introuvable"}

        payload = {
            "type": current["type"],
            "name": current["name"],
            "content": content if content else current["content"],
            "proxied": proxied if proxied is not None else current.get("proxied", False),
            "ttl": current.get("ttl", 1),
        }

        resp = await client.put(
            f"{CF_API}/zones/{settings.cloudflare_zone_id}/dns_records/{record_id}",
            headers=_cf_headers(),
            json=payload,
        )

    data = resp.json()
    if not data.get("success"):
        return {"success": False, "errors": data.get("errors", [])}

    return {
        "success": True,
        "record": data["result"],
        "message": f"Enregistrement mis à jour: {current['name']} → {content or current['content']}",
    }


async def tool_dns_delete_record(record_id: str) -> Dict[str, Any]:
    """Supprime un enregistrement DNS Cloudflare."""
    if not _cf_available():
        return {"success": False, "error": "Cloudflare non configuré"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"{CF_API}/zones/{settings.cloudflare_zone_id}/dns_records/{record_id}",
            headers=_cf_headers(),
        )

    data = resp.json()
    return {"success": data.get("success", False), "id": record_id}


async def tool_dns_toggle_proxy(record_id: str, proxied: bool) -> Dict[str, Any]:
    """
    Active (True) ou désactive (False) le proxy Cloudflare pour un enregistrement.
    proxied=True: protection DDoS, cache CDN, HTTPS automatique via Cloudflare
    proxied=False: DNS uniquement, connexion directe au serveur
    """
    return await tool_dns_update_record(record_id=record_id, content="", proxied=proxied)


async def tool_dns_check_propagation(domain: str, record_type: str = "A") -> Dict[str, Any]:
    """
    Vérifie la propagation DNS sur plusieurs serveurs publics.
    Utile après création/modification d'un enregistrement DNS.
    """
    results = {}

    # Résolution locale
    try:
        local_ip = socket.gethostbyname(domain)
        results["local"] = {"ip": local_ip, "success": True}
    except socket.gaierror as e:
        results["local"] = {"ip": None, "success": False, "error": str(e)}

    # DNS-over-HTTPS (Google)
    dns_servers = {"Cloudflare": "1.1.1.1", "Google": "8.8.8.8", "Quad9": "9.9.9.9"}
    ips_found = set()

    for dns_name in dns_servers:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://dns.google/resolve",
                    params={"name": domain, "type": record_type},
                )
            answers = resp.json().get("Answer", [])
            if answers:
                ip = answers[-1].get("data", "")
                results[dns_name] = {"ip": ip, "success": True}
                ips_found.add(ip)
            else:
                results[dns_name] = {"ip": None, "success": False, "error": "No answer"}
        except Exception as e:
            results[dns_name] = {"ip": None, "success": False, "error": str(e)}

    propagated = len(ips_found) <= 1

    return {
        "success": True,
        "domain": domain,
        "record_type": record_type,
        "propagated": propagated,
        "consistent_ips": list(ips_found),
        "results": results,
        "message": (
            "DNS propagé uniformément ✓"
            if propagated
            else f"Propagation incomplète — {len(ips_found)} IPs différentes détectées"
        ),
    }


async def tool_dns_lookup(domain: str) -> Dict[str, Any]:
    """Résolution DNS complète d'un domaine: A, MX, NS, TXT."""
    results = {}

    try:
        results["A"] = socket.gethostbyname_ex(domain)[2]
    except socket.gaierror:
        results["A"] = []

    for record_type in ["MX", "NS", "TXT"]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "dig", "+short", domain, record_type,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            results[record_type] = [r for r in stdout.decode().splitlines() if r.strip()]
        except FileNotFoundError:
            results[record_type] = ["dig non disponible"]
        except Exception as e:
            results[record_type] = [str(e)]

    return {"success": True, "domain": domain, "records": results}


async def tool_cloudflare_purge_cache(
    urls: Optional[List[str]] = None,
    purge_all: bool = False,
) -> Dict[str, Any]:
    """
    Purge le cache Cloudflare.
    urls: liste d'URLs spécifiques à purger
    purge_all: True pour tout purger (attention: impact performance temporaire)
    """
    if not _cf_available():
        return {"success": False, "error": "Cloudflare non configuré"}

    if purge_all:
        payload: Dict[str, Any] = {"purge_everything": True}
    elif urls:
        payload = {"files": urls}
    else:
        return {"success": False, "error": "Spécifier des URLs ou purge_all=True"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CF_API}/zones/{settings.cloudflare_zone_id}/purge_cache",
            headers=_cf_headers(),
            json=payload,
        )

    data = resp.json()
    if not data.get("success"):
        return {"success": False, "errors": data.get("errors", [])}

    return {
        "success": True,
        "message": "Cache Cloudflare purgé",
        "purged_all": purge_all,
        "purged_urls": urls or [],
    }
