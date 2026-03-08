"""
Outils de gestion des bases de données — Karl peut inspecter, optimiser
et gérer les BDD tournant dans les conteneurs Docker du VPS.
"""
from typing import Any, Dict, Optional

from tools.vps_tools import _agent_client


async def tool_database_list(container: str, db_type: str) -> Dict[str, Any]:
    """
    Liste les bases de données dans un conteneur.
    db_type: postgresql | mysql | mongodb | redis
    container: nom du conteneur Docker (ex: myapp-postgres-1)
    """
    async with _agent_client() as client:
        resp = await client.get("/database/list", params={"container": container, "db_type": db_type})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_stats(container: str, db_type: str) -> Dict[str, Any]:
    """
    Retourne les statistiques générales d'une base de données:
    version, uptime, connexions actives, taille des BDD, cache hit ratio.
    """
    async with _agent_client() as client:
        resp = await client.get(f"/database/stats/{container}", params={"db_type": db_type})
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_slow_queries(
    container: str,
    db_type: str = "postgresql",
    threshold_ms: int = 1000,
) -> Dict[str, Any]:
    """
    Affiche les requêtes SQL lentes en cours d'exécution.
    threshold_ms: seuil en millisecondes pour considérer une requête comme lente (défaut: 1000ms)
    Utile pour identifier les goulets d'étranglement de performance.
    """
    async with _agent_client() as client:
        resp = await client.get(
            f"/database/slow-queries/{container}",
            params={"db_type": db_type, "threshold_ms": threshold_ms},
        )
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_connections(container: str, db_type: str) -> Dict[str, Any]:
    """
    Retourne les connexions actives à la base de données.
    Permet de voir qui est connecté et ce qu'il fait.
    """
    async with _agent_client() as client:
        resp = await client.get(
            f"/database/connections/{container}", params={"db_type": db_type}
        )
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_query(
    container: str,
    db_type: str,
    db_name: str,
    query: str,
    user: str = "postgres",
) -> Dict[str, Any]:
    """
    Exécute une requête SELECT sur la base de données.
    ATTENTION: uniquement les requêtes SELECT sont autorisées (pas de DROP/DELETE/UPDATE).
    db_type: postgresql | mysql
    """
    async with _agent_client() as client:
        resp = await client.post("/database/query", json={
            "container": container,
            "db_type": db_type,
            "db_name": db_name,
            "query": query,
            "user": user,
        })
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_optimize(
    container: str,
    db_type: str,
    db_name: str,
) -> Dict[str, Any]:
    """
    Lance une optimisation de la base de données:
    - PostgreSQL: VACUUM ANALYZE (nettoie les tuples morts, met à jour les stats)
    - MySQL: OPTIMIZE ALL DATABASES
    Recommandé après de nombreuses suppressions/mises à jour.
    """
    async with _agent_client() as client:
        resp = await client.post("/database/optimize", json={
            "container": container,
            "db_type": db_type,
            "db_name": db_name,
        })
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_dump(
    db_type: str,
    container: str,
    db_name: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée un dump (sauvegarde) d'une base de données.
    db_type: postgresql | mysql | mongodb | sqlite
    Le fichier est sauvegardé dans /backups/databases/ sur le VPS.
    """
    async with _agent_client() as client:
        resp = await client.post("/database/dump", json={
            "db_type": db_type,
            "container": container,
            "db_name": db_name,
            "user": user,
            "password": password,
        })
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_restore(
    backup_file: str,
    db_type: str,
    container: str,
    db_name: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Restaure une base de données depuis un fichier de sauvegarde.
    backup_file: chemin du fichier dans /backups/databases/ sur le VPS.
    ATTENTION: opération irréversible — effectue un dump de sécurité avant restauration.
    """
    async with _agent_client() as client:
        resp = await client.post("/database/restore", json={
            "backup_file": backup_file,
            "db_type": db_type,
            "container": container,
            "db_name": db_name,
            "user": user,
            "password": password,
        })
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}


async def tool_database_size(
    container: str,
    db_type: str,
    db_name: str,
) -> Dict[str, Any]:
    """
    Retourne la taille d'une base de données spécifique.
    """
    async with _agent_client() as client:
        resp = await client.get(
            f"/database/size/{container}",
            params={"db_type": db_type, "db_name": db_name},
        )
    return resp.json() if resp.status_code == 200 else {"success": False, "error": resp.text}
