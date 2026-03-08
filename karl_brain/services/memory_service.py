"""
Service de mémoire infrastructure — Karl se souvient de l'état du serveur,
des décisions prises, des configurations appliquées, des incidents résolus.
Permet une continuité entre les conversations.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite

from core.database import DATABASE_URL

logger = logging.getLogger("karl.memory")

# On extrait le path du fichier depuis l'URL SQLite (ex: "sqlite:///./karl.db" → "./karl.db")
_DB_PATH = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")


async def _get_db() -> aiosqlite.Connection:
    return await aiosqlite.connect(_DB_PATH)


async def init_memory_table() -> None:
    """Crée la table knowledge_base si elle n'existe pas."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_kb_key ON knowledge_base(key)
        """)
        await db.commit()
    logger.info("Memory table initialized")


# ── Catégories de mémoire ──────────────────────────────────────────────────────
# infrastructure  → config serveur, specs, IP, etc.
# deployments     → apps déployées, ports, domaines
# incidents       → problèmes résolus, causes racines
# decisions       → choix techniques pris
# configs         → configs nginx, docker, etc. sauvegardées
# notes           → notes libres


async def remember(
    category: str,
    key: str,
    value: Any,
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Sauvegarde ou met à jour une information en mémoire."""
    value_str = json.dumps(value) if not isinstance(value, str) else value
    meta_str = json.dumps(metadata or {})

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            INSERT INTO knowledge_base (category, key, value, metadata, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(category, key) DO UPDATE SET
                value = excluded.value,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (category, key, value_str, meta_str))
        await db.commit()

    logger.info(f"Memory saved: [{category}] {key}")
    return {"success": True, "category": category, "key": key}


async def recall(
    category: Optional[str] = None,
    key: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Récupère des informations de la mémoire."""
    query = "SELECT category, key, value, metadata, created_at, updated_at FROM knowledge_base"
    params = []
    conditions = []

    if category:
        conditions.append("category = ?")
        params.append(category)
    if key:
        conditions.append("key LIKE ?")
        params.append(f"%{key}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    results = []
    for row in rows:
        try:
            value = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            value = row["value"]

        try:
            metadata = json.loads(row["metadata"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        results.append({
            "category": row["category"],
            "key": row["key"],
            "value": value,
            "metadata": metadata,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return results


async def forget(category: str, key: str) -> Dict[str, Any]:
    """Supprime une information de la mémoire."""
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM knowledge_base WHERE category = ? AND key = ?",
            (category, key),
        )
        await db.commit()
        deleted = cursor.rowcount

    return {"success": deleted > 0, "deleted": deleted, "category": category, "key": key}


async def search_memory(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Recherche dans toute la mémoire (full-text sur key + value)."""
    pattern = f"%{query}%"
    sql = """
        SELECT category, key, value, metadata, updated_at
        FROM knowledge_base
        WHERE key LIKE ? OR value LIKE ?
        ORDER BY updated_at DESC
        LIMIT ?
    """

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, (pattern, pattern, limit)) as cursor:
            rows = await cursor.fetchall()

    results = []
    for row in rows:
        try:
            value = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            value = row["value"]
        results.append({
            "category": row["category"],
            "key": row["key"],
            "value": value,
            "updated_at": row["updated_at"],
        })

    return results


async def get_infrastructure_summary() -> Dict[str, Any]:
    """Retourne un résumé de la connaissance infrastructure pour le context LLM."""
    categories = ["infrastructure", "deployments", "incidents", "decisions"]
    summary = {}

    for cat in categories:
        items = await recall(category=cat, limit=20)
        if items:
            summary[cat] = {item["key"]: item["value"] for item in items}

    return summary


# ── Helpers pour auto-mémorisation ────────────────────────────────────────────

async def record_deployment(
    app_name: str,
    domain: str,
    port: int,
    tech_stack: str,
    environment: str = "production",
) -> None:
    """Mémorise automatiquement un déploiement."""
    await remember(
        category="deployments",
        key=app_name,
        value={
            "domain": domain,
            "port": port,
            "tech_stack": tech_stack,
            "environment": environment,
            "deployed_at": datetime.now().isoformat(),
        },
    )


async def record_incident(
    title: str,
    description: str,
    resolution: str,
    affected_services: List[str],
) -> None:
    """Mémorise un incident et sa résolution."""
    key = f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    await remember(
        category="incidents",
        key=key,
        value={
            "title": title,
            "description": description,
            "resolution": resolution,
            "affected_services": affected_services,
            "resolved_at": datetime.now().isoformat(),
        },
    )
