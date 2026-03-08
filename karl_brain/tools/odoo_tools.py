"""
Intégration Odoo CRM via XML-RPC.
Gestion des prospects/leads.
"""
import xmlrpc.client
from typing import Dict, Any, Optional, List

from core.config import get_settings

settings = get_settings()


def _get_odoo_client():
    """Retourne les clients XML-RPC Odoo."""
    if not settings.odoo_url:
        raise ValueError("Odoo non configuré. Définir ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY dans .env")

    common = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(
        settings.odoo_db,
        settings.odoo_username,
        settings.odoo_api_key,
        {},
    )
    if not uid:
        raise ValueError("Authentification Odoo échouée. Vérifier les credentials.")

    models = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/object")
    return models, uid


async def odoo_create_prospect(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    description: Optional[str] = None,
    stage: Optional[str] = None,
    expected_revenue: Optional[float] = None,
) -> Dict[str, Any]:
    """Crée un nouveau lead/prospect dans Odoo CRM."""
    import asyncio

    def _create():
        models, uid = _get_odoo_client()

        vals = {
            "name": name,
            "type": "lead",
        }
        if email:
            vals["email_from"] = email
        if phone:
            vals["phone"] = phone
        if company:
            vals["partner_name"] = company
        if description:
            vals["description"] = description
        if expected_revenue is not None:
            vals["expected_revenue"] = expected_revenue

        # Trouver l'étape si spécifiée
        if stage:
            stage_ids = models.execute_kw(
                settings.odoo_db, uid, settings.odoo_api_key,
                "crm.stage", "search_read",
                [[["name", "ilike", stage]]],
                {"fields": ["id", "name"], "limit": 1},
            )
            if stage_ids:
                vals["stage_id"] = stage_ids[0]["id"]

        lead_id = models.execute_kw(
            settings.odoo_db, uid, settings.odoo_api_key,
            "crm.lead", "create", [vals],
        )

        return {
            "success": True,
            "lead_id": lead_id,
            "name": name,
            "message": f"Prospect '{name}' créé avec l'ID {lead_id}",
        }

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _create)
    except Exception as e:
        return {"success": False, "error": str(e)}


async def odoo_list_prospects(
    limit: int = 20,
    stage: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Liste les prospects dans Odoo CRM."""
    import asyncio

    def _list():
        models, uid = _get_odoo_client()

        domain = [["type", "=", "lead"]]
        if search:
            domain.append(["name", "ilike", search])
        if stage:
            domain.append(["stage_id.name", "ilike", stage])

        leads = models.execute_kw(
            settings.odoo_db, uid, settings.odoo_api_key,
            "crm.lead", "search_read",
            [domain],
            {
                "fields": [
                    "id", "name", "email_from", "phone", "partner_name",
                    "stage_id", "expected_revenue", "probability",
                    "date_deadline", "create_date", "user_id",
                ],
                "limit": limit,
                "order": "create_date desc",
            },
        )

        return {
            "success": True,
            "total": len(leads),
            "prospects": leads,
        }

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _list)
    except Exception as e:
        return {"success": False, "error": str(e)}


async def odoo_update_prospect(
    prospect_id: int,
    fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Met à jour un prospect Odoo."""
    import asyncio

    def _update():
        models, uid = _get_odoo_client()

        result = models.execute_kw(
            settings.odoo_db, uid, settings.odoo_api_key,
            "crm.lead", "write",
            [[prospect_id], fields],
        )

        return {
            "success": bool(result),
            "prospect_id": prospect_id,
            "updated_fields": list(fields.keys()),
        }

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _update)
    except Exception as e:
        return {"success": False, "error": str(e)}
