"""Outils de gestion du pare-feu UFW via le VPS Agent."""
import httpx
from typing import Any, Dict, Optional
from core.config import get_settings

settings = get_settings()

def _agent(): return httpx.AsyncClient(
    base_url=settings.vps_agent_url,
    headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
    timeout=15,
)

async def tool_firewall_status() -> Dict[str, Any]:
    async with _agent() as c:
        r = await c.get("/firewall/status")
        return r.json() if r.status_code == 200 else {"error": r.text}

async def tool_firewall_list_rules() -> Dict[str, Any]:
    async with _agent() as c:
        r = await c.get("/firewall/rules")
        return r.json() if r.status_code == 200 else {"error": r.text}

async def tool_firewall_add_rule(
    action: str, port: Optional[int] = None,
    proto: str = "tcp", from_ip: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {"action": action, "port": port, "proto": proto, "from_ip": from_ip}
    async with _agent() as c:
        r = await c.post("/firewall/rules", json={k: v for k, v in payload.items() if v is not None})
        return r.json() if r.status_code == 200 else {"error": r.text}

async def tool_firewall_block_ip(ip: str) -> Dict[str, Any]:
    async with _agent() as c:
        r = await c.post("/firewall/block-ip", params={"ip": ip})
        return r.json() if r.status_code == 200 else {"error": r.text}

async def tool_firewall_detect_brute_force() -> Dict[str, Any]:
    async with _agent() as c:
        r = await c.get("/firewall/brute-force")
        return r.json() if r.status_code == 200 else {"error": r.text}
