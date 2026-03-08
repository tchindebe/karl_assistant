"""
Outils SSL avancés — suivi des certificats, alertes d'expiration,
vérification externe, renouvellement forcé.
"""
from typing import Any, Dict

from tools.vps_tools import _agent_client


async def enable_ssl(domain: str, email: str) -> Dict[str, Any]:
    """Fonction interne réutilisable pour activer SSL."""
    async with _agent_client() as client:
        resp = await client.post("/ssl/enable", json={"domain": domain, "email": email})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_ssl_list_certificates() -> Dict[str, Any]:
    """
    Liste tous les certificats SSL Let's Encrypt installés sur le VPS.
    Affiche: domaines, date d'expiration, jours restants, statut.
    """
    async with _agent_client() as client:
        resp = await client.get("/ssl")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_ssl_check_expiry() -> Dict[str, Any]:
    """
    Vérifie l'expiration de tous les certificats SSL.
    Retourne des alertes pour les certificats:
    - Expirés (critique)
    - Expirant dans < 7 jours (critique)
    - Expirant dans < 30 jours (avertissement)
    Utile pour anticiper les renouvellements avant interruption de service.
    """
    async with _agent_client() as client:
        resp = await client.get("/ssl/expiry")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_ssl_check_domain(domain: str, port: int = 443) -> Dict[str, Any]:
    """
    Vérifie le certificat SSL d'un domaine depuis l'extérieur (via openssl).
    Retourne: émetteur, date d'expiration, jours restants, statut.
    Utile pour vérifier un certificat externe ou tiers.
    domain: nom de domaine (ex: app.example.com)
    """
    async with _agent_client() as client:
        resp = await client.get("/ssl/check-domain", params={"domain": domain, "port": port})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_ssl_enable(domain: str, email: str) -> Dict[str, Any]:
    """
    Obtient un certificat SSL Let's Encrypt pour un domaine.
    Configure automatiquement Nginx pour HTTPS + redirection HTTP→HTTPS.
    Prérequis: le domaine doit pointer vers le VPS et Nginx doit être configuré.
    """
    return await enable_ssl(domain, email)


async def tool_ssl_renew_all() -> Dict[str, Any]:
    """
    Renouvelle tous les certificats SSL arrivant à expiration.
    Certbot ne renouvelle que les certificats expirant dans < 30 jours.
    Idempotent: sans danger à appeler régulièrement.
    """
    async with _agent_client() as client:
        resp = await client.post("/ssl/renew")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_ssl_force_renew(domain: str) -> Dict[str, Any]:
    """
    Force le renouvellement d'un certificat spécifique.
    Ignore la date d'expiration — renouvelle même si encore valide longtemps.
    Utile si le certificat pose problème ou a été révoqué.
    """
    async with _agent_client() as client:
        resp = await client.post("/ssl/force-renew", json={"domain": domain})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_ssl_revoke(domain: str) -> Dict[str, Any]:
    """
    Révoque et supprime un certificat SSL.
    ATTENTION: opération irréversible — le domaine repassera en HTTP.
    Utiliser uniquement si le certificat est compromis ou le domaine abandonné.
    """
    async with _agent_client() as client:
        resp = await client.post("/ssl/revoke", json={"domain": domain})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}
