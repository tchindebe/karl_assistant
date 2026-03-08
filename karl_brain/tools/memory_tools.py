"""
Outils de mémoire infrastructure — Karl peut se souvenir et rappeler
des informations sur le serveur entre les conversations.
"""
from typing import Any, Dict, List, Optional

from services.memory_service import (
    forget,
    get_infrastructure_summary,
    recall,
    record_incident,
    remember,
    search_memory,
)


async def tool_remember(
    category: str,
    key: str,
    value: Any,
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Sauvegarde une information en mémoire persistante.
    categories: infrastructure | deployments | incidents | decisions | configs | notes
    Exemple: category="deployments", key="my-app", value={"domain": "app.example.com", "port": 3000}
    """
    return await remember(category=category, key=key, value=value, metadata=metadata)


async def tool_recall(
    category: Optional[str] = None,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rappelle des informations de la mémoire.
    Sans filtres: retourne tout. Avec category: filtre par catégorie. Avec key: recherche par clé.
    """
    items = await recall(category=category, key=key)
    return {
        "success": True,
        "count": len(items),
        "memories": items,
    }


async def tool_forget(category: str, key: str) -> Dict[str, Any]:
    """Supprime une information de la mémoire."""
    return await forget(category=category, key=key)


async def tool_search_memory(query: str) -> Dict[str, Any]:
    """
    Recherche dans toute la mémoire.
    Retourne les entrées dont la clé ou la valeur contient le terme recherché.
    """
    results = await search_memory(query)
    return {
        "success": True,
        "query": query,
        "count": len(results),
        "results": results,
    }


async def tool_get_infrastructure_summary() -> Dict[str, Any]:
    """
    Retourne un résumé complet de la connaissance infrastructure:
    apps déployées, incidents passés, décisions techniques, config serveur.
    Utile pour que Karl ait le contexte complet en début de conversation.
    """
    summary = await get_infrastructure_summary()
    return {
        "success": True,
        "summary": summary,
        "categories": list(summary.keys()),
    }


async def tool_record_incident(
    title: str,
    description: str,
    resolution: str,
    affected_services: List[str],
) -> Dict[str, Any]:
    """
    Enregistre un incident résolu pour référence future.
    Karl pourra s'en souvenir lors de problèmes similaires.
    """
    await record_incident(
        title=title,
        description=description,
        resolution=resolution,
        affected_services=affected_services,
    )
    return {
        "success": True,
        "message": f"Incident '{title}' mémorisé pour référence future.",
    }
