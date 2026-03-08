"""
Outils d'audit de sécurité — Karl peut analyser la posture de sécurité
du VPS et fournir des recommandations concrètes.
"""
from typing import Any, Dict, Optional

from tools.vps_tools import _agent_client


async def tool_security_full_audit() -> Dict[str, Any]:
    """
    Lance un audit de sécurité complet du VPS:
    - Ports ouverts et services exposés
    - Images Docker (root, tags latest, dangling)
    - Permissions fichiers sensibles (/etc/shadow, sshd_config...)
    - Configuration SSH (PermitRootLogin, PasswordAuthentication...)
    - Mises à jour système disponibles
    - Tentatives de connexion échouées (brute force)

    Retourne un score de sécurité (0-100) et un grade (A-F) avec
    la liste des problèmes par niveau de sévérité.
    """
    async with _agent_client() as client:
        resp = await client.get("/security/audit")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_check_open_ports() -> Dict[str, Any]:
    """
    Vérifie les ports ouverts sur le VPS et identifie les services exposés.
    Détecte les ports dangereux (FTP, Telnet, BDD exposées publiquement).
    Fournit des recommandations pour restreindre l'accès.
    """
    async with _agent_client() as client:
        resp = await client.get("/security/open-ports")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_check_docker() -> Dict[str, Any]:
    """
    Analyse la sécurité des conteneurs Docker:
    - Conteneurs tournant en tant que root (risque élevé)
    - Images avec tag 'latest' (non reproductible)
    - Images dangling (orphelines)
    Fournit des recommandations pour chaque problème détecté.
    """
    async with _agent_client() as client:
        resp = await client.get("/security/docker-images")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_check_file_permissions() -> Dict[str, Any]:
    """
    Vérifie les permissions des fichiers sensibles:
    /etc/shadow, /etc/sudoers, /etc/ssh/sshd_config, ~/.ssh/authorized_keys
    Détecte les fichiers SUID inattendus.
    """
    async with _agent_client() as client:
        resp = await client.get("/security/file-permissions")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_check_ssh() -> Dict[str, Any]:
    """
    Analyse la configuration SSH pour les bonnes pratiques:
    - PermitRootLogin doit être 'no'
    - PasswordAuthentication doit être 'no' (clés SSH uniquement)
    - PermitEmptyPasswords doit être 'no'
    - Protocol doit être 2
    Retourne les paramètres actuels et les corrections recommandées.
    """
    async with _agent_client() as client:
        resp = await client.get("/security/ssh-config")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_check_failed_logins(hours: int = 24) -> Dict[str, Any]:
    """
    Analyse les tentatives de connexion SSH échouées.
    Identifie les IPs qui font du brute-force.
    Recommande des actions (fail2ban, blocage IP via pare-feu).
    hours: période d'analyse en heures (défaut: 24h)
    """
    async with _agent_client() as client:
        resp = await client.get("/security/failed-logins", params={"hours": hours})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_check_updates() -> Dict[str, Any]:
    """
    Vérifie les mises à jour système disponibles.
    Identifie les mises à jour de sécurité critiques.
    Fournit les commandes pour les appliquer.
    """
    async with _agent_client() as client:
        resp = await client.get("/security/system-updates")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_harden_ssh() -> Dict[str, Any]:
    """
    Applique automatiquement les bonnes pratiques de sécurité SSH:
    - Désactive la connexion root
    - Désactive l'authentification par mot de passe
    - Désactive X11 forwarding
    ATTENTION: Assurez-vous d'avoir une clé SSH configurée avant d'exécuter!
    Redémarre le service SSH après modification.
    """
    async with _agent_client() as client:
        resp = await client.post("/security/harden-ssh")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_install_fail2ban() -> Dict[str, Any]:
    """
    Installe et configure fail2ban pour protéger contre les attaques brute-force.
    Configure la protection SSH avec bannissement après 5 tentatives échouées.
    """
    async with _agent_client() as client:
        resp = await client.post("/security/install-fail2ban")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_security_scan_malware() -> Dict[str, Any]:
    """
    Lance une analyse rapide pour détecter des indicateurs de compromission:
    - Fichiers récemment modifiés dans les répertoires système
    - Processus cachés ou suspects
    - Connexions réseau suspectes
    - Tâches CRON non autorisées
    """
    async with _agent_client() as client:
        resp = await client.get("/security/malware-scan")
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}
