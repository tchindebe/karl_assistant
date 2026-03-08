"""
Endpoint métriques — proxy vers le VPS Agent pour le dashboard.
"""
from fastapi import APIRouter, Depends
from core.security import get_current_user
from tools.vps_tools import get_server_metrics

router = APIRouter()


@router.get("/api/metrics")
async def metrics(current_user: str = Depends(get_current_user)):
    return await get_server_metrics()
