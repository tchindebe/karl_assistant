"""
App Store — déploiement one-click d'applications pré-configurées.
"""
from typing import Any, Dict, List, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "docker"

# Catalogue des applications disponibles
APP_CATALOG: Dict[str, Dict[str, Any]] = {
    "wordpress": {
        "name": "WordPress",
        "description": "CMS le plus populaire au monde. Blog, site vitrine, e-commerce.",
        "template": "wordpress.yml.j2",
        "default_port": 8080,
        "requires": ["MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"],
        "optional": ["MYSQL_DATABASE", "MYSQL_USER"],
        "tags": ["cms", "blog", "php", "mysql"],
        "ram_min_mb": 512,
    },
    "ghost": {
        "name": "Ghost",
        "description": "Plateforme de publication moderne. Newsletter + blog.",
        "template": "ghost.yml.j2",
        "default_port": 8081,
        "requires": ["DB_PASSWORD"],
        "optional": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
        "tags": ["blog", "newsletter", "node"],
        "ram_min_mb": 512,
    },
    "nextcloud": {
        "name": "Nextcloud",
        "description": "Cloud personnel. Fichiers, calendrier, contacts, visioconférence.",
        "template": "nextcloud.yml.j2",
        "default_port": 8082,
        "requires": ["DB_PASSWORD", "ADMIN_PASSWORD"],
        "optional": ["ADMIN_USER"],
        "tags": ["cloud", "files", "collaboration"],
        "ram_min_mb": 1024,
    },
    "n8n": {
        "name": "n8n",
        "description": "Automatisation de workflows. Alternative open-source à Zapier.",
        "template": "n8n.yml.j2",
        "default_port": 8083,
        "requires": ["N8N_PASSWORD", "DB_PASSWORD"],
        "optional": ["N8N_USER", "TIMEZONE"],
        "tags": ["automation", "workflow", "integration"],
        "ram_min_mb": 512,
    },
    "gitea": {
        "name": "Gitea",
        "description": "Hébergeur Git self-hosted. Léger et rapide.",
        "template": "gitea.yml.j2",
        "default_port": 8084,
        "requires": ["DB_PASSWORD"],
        "optional": ["SSH_PORT"],
        "tags": ["git", "devops", "code"],
        "ram_min_mb": 256,
    },
    "uptime-kuma": {
        "name": "Uptime Kuma",
        "description": "Monitoring d'uptime. Vérifie la disponibilité de vos services.",
        "template": "uptime-kuma.yml.j2",
        "default_port": 8085,
        "requires": [],
        "optional": [],
        "tags": ["monitoring", "uptime", "alerting"],
        "ram_min_mb": 128,
    },
    "nodejs": {
        "name": "Node.js App",
        "description": "Application Node.js générique.",
        "template": "nodejs.yml.j2",
        "default_port": 3000,
        "requires": [],
        "optional": ["NODE_ENV"],
        "tags": ["nodejs", "javascript", "api"],
        "ram_min_mb": 256,
    },
    "python": {
        "name": "Python App",
        "description": "Application Python / FastAPI / Django / Flask générique.",
        "template": "python.yml.j2",
        "default_port": 8000,
        "requires": [],
        "optional": [],
        "tags": ["python", "fastapi", "django", "api"],
        "ram_min_mb": 256,
    },
    "static": {
        "name": "Site statique",
        "description": "Site HTML/CSS/JS servi par Nginx.",
        "template": "static.yml.j2",
        "default_port": 80,
        "requires": [],
        "optional": [],
        "tags": ["static", "html", "nginx"],
        "ram_min_mb": 64,
    },
}


async def tool_list_available_apps(tag: Optional[str] = None) -> Dict[str, Any]:
    """Liste les applications disponibles dans l'App Store."""
    apps = []
    for app_id, meta in APP_CATALOG.items():
        if tag and tag not in meta.get("tags", []):
            continue
        apps.append({
            "id": app_id,
            "name": meta["name"],
            "description": meta["description"],
            "tags": meta["tags"],
            "default_port": meta["default_port"],
            "requires": meta["requires"],
            "ram_min_mb": meta["ram_min_mb"],
        })
    return {"apps": apps, "count": len(apps)}


async def tool_get_app_info(app_id: str) -> Dict[str, Any]:
    """Retourne les détails d'une application du catalogue."""
    if app_id not in APP_CATALOG:
        return {"error": f"Application '{app_id}' inconnue. Utilisez list_available_apps."}
    return APP_CATALOG[app_id]


async def tool_install_app(
    app_id: str,
    instance_name: str,
    port: int,
    domain: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    environment: str = "production",
    enable_ssl: bool = False,
    ssl_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Installe une application depuis le catalogue.
    Génère le docker-compose, déploie et configure Nginx+SSL.
    """
    if app_id not in APP_CATALOG:
        return {"error": f"Application '{app_id}' inconnue."}

    app_meta = APP_CATALOG[app_id]
    env_vars = env_vars or {}

    # Vérifier les variables requises
    missing = [r for r in app_meta["requires"] if r not in env_vars]
    if missing:
        return {
            "error": f"Variables d'environnement manquantes pour {app_meta['name']}: {missing}",
            "required": app_meta["requires"],
        }

    # Générer le compose depuis le template
    try:
        jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        template = jinja_env.get_template(app_meta["template"])
        compose_content = template.render(
            name=instance_name,
            port=port,
            domain=domain or "",
            env_vars=env_vars,
            environment=environment,
        )
    except Exception as e:
        return {"error": f"Erreur génération template: {e}"}

    # Déployer via VPS Agent
    import httpx
    from core.config import get_settings
    s = get_settings()

    async with httpx.AsyncClient(
        base_url=s.vps_agent_url,
        headers={"Authorization": f"Bearer {s.vps_agent_api_key}"},
        timeout=300,
    ) as client:
        # 1. Déployer l'app
        deploy_resp = await client.post("/deploy", json={
            "name": instance_name,
            "compose_content": compose_content,
            "env_vars": env_vars,
            "environment": environment,
        })
        deploy_result = deploy_resp.json() if deploy_resp.status_code == 200 else {"error": deploy_resp.text}

        # 2. Configurer Nginx si domaine fourni
        nginx_result = None
        if domain:
            nginx_resp = await client.post("/nginx/configure", json={
                "domain": domain,
                "upstream_port": port,
                "ssl": False,
                "websocket": False,
            })
            nginx_result = nginx_resp.json() if nginx_resp.status_code == 200 else {"error": nginx_resp.text}

        # 3. SSL si demandé
        ssl_result = None
        if enable_ssl and domain and ssl_email:
            ssl_resp = await client.post("/ssl/enable", json={"domain": domain, "email": ssl_email})
            ssl_result = ssl_resp.json() if ssl_resp.status_code == 200 else {"error": ssl_resp.text}

    return {
        "app": app_meta["name"],
        "instance": instance_name,
        "port": port,
        "domain": domain,
        "environment": environment,
        "deploy": deploy_result,
        "nginx": nginx_result,
        "ssl": ssl_result,
        "access_url": f"https://{domain}" if (enable_ssl and domain) else (f"http://{domain}" if domain else f"http://localhost:{port}"),
    }
