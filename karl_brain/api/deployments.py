"""
Endpoint déploiements — liste les apps et containers.
"""
from fastapi import APIRouter, Depends
from core.security import get_current_user
from tools.vps_tools import list_deployments, get_logs
from tools.vps_tools import manage_container as _manage_container

router = APIRouter()


@router.get("/api/deployments")
async def deployments(current_user: str = Depends(get_current_user)):
    return await list_deployments()


@router.get("/api/logs/{service}")
async def logs(
    service: str,
    lines: int = 100,
    since: str | None = None,
    current_user: str = Depends(get_current_user),
):
    return await get_logs(service, lines, since)


@router.post("/api/containers/{name}/{action}")
async def manage_container(
    name: str,
    action: str,
    current_user: str = Depends(get_current_user),
):
    return await _manage_container(name, action)
