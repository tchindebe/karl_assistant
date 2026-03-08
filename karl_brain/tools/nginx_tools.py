"""
Outils Nginx — configure le reverse proxy via le VPS Agent.
"""
import httpx
from typing import Dict, Any

from core.config import get_settings

settings = get_settings()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.vps_agent_url,
        headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
        timeout=60,
    )


async def configure_nginx(
    domain: str,
    upstream_port: int,
    ssl: bool = False,
    websocket: bool = False,
    upstream_host: str = "127.0.0.1",
) -> Dict[str, Any]:
    async with _client() as client:
        resp = await client.post(
            "/nginx/configure",
            json={
                "domain": domain,
                "upstream_port": upstream_port,
                "ssl": ssl,
                "websocket": websocket,
                "upstream_host": upstream_host,
            },
        )
        resp.raise_for_status()
        return resp.json()
