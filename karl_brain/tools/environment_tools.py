"""
Outils multi-environnements — Karl gère production, staging, dev
avec des configurations et des déploiements séparés.
"""
from typing import Any, Dict, List, Optional

from tools.vps_tools import _agent_client


# Environnements supportés
ENVIRONMENTS = ["production", "staging", "dev", "testing"]


async def tool_list_environments() -> Dict[str, Any]:
    """
    Liste tous les environnements déployés sur le VPS.
    Regroupe les applications par environnement (production, staging, dev).
    """
    async with _agent_client() as client:
        resp = await client.get("/deployments")

    if resp.status_code != 200:
        return {"success": False, "error": resp.text}

    deployments = resp.json()
    if isinstance(deployments, dict):
        deployments = deployments.get("deployments", [])

    # Grouper par environnement basé sur le nom (convention: app-staging, app-dev, app)
    environments: Dict[str, List] = {env: [] for env in ENVIRONMENTS}
    environments["production"] = []
    environments["other"] = []

    for dep in deployments:
        name = dep.get("name", "")
        env = "production"
        for e in ["staging", "dev", "testing"]:
            if f"-{e}" in name or name.endswith(f".{e}"):
                env = e
                break
        environments.setdefault(env, []).append(dep)

    # Nettoyer les envs vides
    environments = {k: v for k, v in environments.items() if v}

    return {
        "success": True,
        "environments": environments,
        "summary": {env: len(apps) for env, apps in environments.items()},
    }


async def tool_deploy_to_environment(
    app_name: str,
    compose_content: str,
    environment: str,
    env_vars: Optional[Dict[str, str]] = None,
    domain: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Déploie une application dans un environnement spécifique.
    Convention de nommage:
    - production: 'myapp'
    - staging: 'myapp-staging'
    - dev: 'myapp-dev'

    Chaque environnement a son propre namespace, domaine et configuration.
    environment: production | staging | dev | testing
    """
    if environment not in ENVIRONMENTS:
        return {
            "success": False,
            "error": f"Environnement invalide: {environment}. Valeurs: {ENVIRONMENTS}",
        }

    # Nommer l'app selon la convention
    full_name = app_name if environment == "production" else f"{app_name}-{environment}"

    # Domaine par défaut selon l'environnement
    if domain is None and environment != "production":
        domain = f"{environment}.{app_name}.example.com"

    # Variables d'environnement additionnelles selon l'env
    merged_vars = {
        "APP_ENV": environment,
        "NODE_ENV": environment if environment != "staging" else "production",
    }
    if env_vars:
        merged_vars.update(env_vars)

    async with _agent_client() as client:
        resp = await client.post("/deploy", json={
            "name": full_name,
            "compose_content": compose_content,
            "env_vars": merged_vars,
            "environment": environment,
            "domain": domain,
            "port": port,
        })

    if resp.status_code != 200:
        return {"success": False, "error": resp.text}

    result = resp.json()
    result["environment"] = environment
    result["full_name"] = full_name
    result["domain"] = domain

    return result


async def tool_promote_to_production(
    app_name: str,
    from_environment: str = "staging",
) -> Dict[str, Any]:
    """
    Promeut une application d'un environnement vers la production.
    Copie la configuration de staging → production.
    ATTENTION: Vérifie que les tests passent avant de promouvoir!
    from_environment: environnement source (défaut: staging)
    """
    if from_environment == "production":
        return {"success": False, "error": "Impossible de promouvoir depuis production"}

    source_name = f"{app_name}-{from_environment}"

    # Récupérer la configuration de l'environnement source
    async with _agent_client() as client:
        # Lire le compose du staging
        compose_resp = await client.get(f"/deployments/{source_name}/compose")

    if compose_resp.status_code != 200:
        return {
            "success": False,
            "error": f"Application {source_name} introuvable",
            "hint": f"Vérifier que '{source_name}' est déployé avec tool_list_environments",
        }

    source_config = compose_resp.json()

    # Déployer en production avec la même config
    async with _agent_client() as client:
        resp = await client.post("/deploy", json={
            "name": app_name,
            "compose_content": source_config.get("compose_content", ""),
            "env_vars": source_config.get("env_vars", {}),
            "environment": "production",
        })

    if resp.status_code != 200:
        return {"success": False, "error": resp.text}

    return {
        "success": True,
        "promoted": app_name,
        "from": from_environment,
        "to": "production",
        "message": f"✅ {app_name} promu de {from_environment} → production avec succès",
    }


async def tool_get_environment_diff(
    app_name: str,
    env1: str = "staging",
    env2: str = "production",
) -> Dict[str, Any]:
    """
    Compare les configurations de deux environnements pour une application.
    Utile pour vérifier les différences avant une promotion staging → production.
    """
    results = {}
    for env in [env1, env2]:
        name = app_name if env == "production" else f"{app_name}-{env}"
        async with _agent_client() as client:
            resp = await client.get(f"/deployments/{name}/compose")
        if resp.status_code == 200:
            results[env] = resp.json()
        else:
            results[env] = {"error": f"{name} non trouvé"}

    if "error" in results.get(env1, {}) or "error" in results.get(env2, {}):
        return {
            "success": False,
            "results": results,
            "hint": "Utiliser tool_list_environments pour voir les apps disponibles",
        }

    return {
        "success": True,
        "app": app_name,
        "comparison": results,
        "message": "Comparer manuellement les configurations ou demander à Karl d'analyser les différences",
    }


async def tool_clone_environment(
    app_name: str,
    source_env: str,
    target_env: str,
) -> Dict[str, Any]:
    """
    Clone un environnement vers un autre (ex: production → staging pour debug).
    Utile pour reproduire un problème de production en staging.
    source_env → target_env
    """
    source_name = app_name if source_env == "production" else f"{app_name}-{source_env}"
    target_name = app_name if target_env == "production" else f"{app_name}-{target_env}"

    async with _agent_client() as client:
        compose_resp = await client.get(f"/deployments/{source_name}/compose")

    if compose_resp.status_code != 200:
        return {"success": False, "error": f"{source_name} introuvable"}

    source_config = compose_resp.json()

    async with _agent_client() as client:
        resp = await client.post("/deploy", json={
            "name": target_name,
            "compose_content": source_config.get("compose_content", ""),
            "env_vars": {
                **source_config.get("env_vars", {}),
                "APP_ENV": target_env,
            },
            "environment": target_env,
        })

    if resp.status_code != 200:
        return {"success": False, "error": resp.text}

    return {
        "success": True,
        "cloned": f"{source_name} → {target_name}",
        "message": f"Environnement {source_env} cloné vers {target_env} avec succès",
    }
