"""
Outils VPS — appellent le Karl VPS Agent via HTTP.
Gèrent: déploiement, containers, logs, métriques, health check.
"""
import httpx
import json
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from core.config import get_settings

settings = get_settings()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "docker"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.vps_agent_url,
        headers={"Authorization": f"Bearer {settings.vps_agent_api_key}"},
        timeout=settings.vps_agent_timeout,
    )


# Alias utilisé par tous les modules tools/* pour accéder au VPS Agent
_agent_client = _client


def _generate_compose(
    name: str,
    stack: str,
    port: int = 3000,
    image: Optional[str] = None,
    env_vars: Dict[str, str] = {},
) -> str:
    """Génère un docker-compose.yml depuis les templates Jinja2."""
    template_map = {
        "nodejs": "nodejs.yml.j2",
        "python": "python.yml.j2",
        "php": "php.yml.j2",
        "static": "static.yml.j2",
    }

    template_name = template_map.get(stack)
    if template_name:
        try:
            tmpl = jinja_env.get_template(template_name)
            return tmpl.render(
                name=name,
                port=port,
                image=image,
                env_vars=env_vars,
            )
        except Exception:
            pass

    # Fallback: compose générique
    env_section = ""
    if env_vars:
        env_lines = "\n".join(f"      - {k}={v}" for k, v in env_vars.items())
        env_section = f"    environment:\n{env_lines}\n"

    default_image = image or {
        "nodejs": "node:20-alpine",
        "python": "python:3.12-slim",
        "php": "php:8.3-apache",
        "static": "nginx:alpine",
    }.get(stack, "alpine")

    return f"""version: "3.8"
services:
  {name}:
    image: {default_image}
    restart: unless-stopped
    ports:
      - "{port}:{port}"
{env_section}    labels:
      - "karl.app={name}"
      - "karl.stack={stack}"
"""


async def deploy_application(
    name: str,
    stack: str,
    compose_content: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    port: int = 3000,
    image: Optional[str] = None,
    pull: bool = True,
) -> Dict[str, Any]:
    env_vars = env_vars or {}

    if not compose_content:
        compose_content = _generate_compose(name, stack, port, image, env_vars)

    async with _client() as client:
        resp = await client.post(
            "/deploy",
            json={
                "name": name,
                "compose_content": compose_content,
                "env_vars": env_vars,
                "pull": pull,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def list_deployments() -> Dict[str, Any]:
    async with _client() as client:
        resp = await client.get("/deployments")
        resp.raise_for_status()
        return resp.json()


async def manage_container(name: str, action: str) -> Dict[str, Any]:
    async with _client() as client:
        resp = await client.post(f"/containers/{name}/{action}")
        resp.raise_for_status()
        return resp.json()


async def get_logs(
    service: str,
    lines: int = 100,
    since: Optional[str] = None,
) -> Dict[str, Any]:
    params = {"lines": lines}
    if since:
        params["since"] = since

    async with _client() as client:
        resp = await client.get(f"/logs/{service}", params=params)
        resp.raise_for_status()
        return resp.json()


async def get_server_metrics() -> Dict[str, Any]:
    async with _client() as client:
        resp = await client.get("/metrics")
        resp.raise_for_status()
        return resp.json()


async def check_health(url: str, expected_status: int = 200) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            return {
                "url": url,
                "status_code": resp.status_code,
                "healthy": resp.status_code == expected_status,
                "response_time_ms": resp.elapsed.total_seconds() * 1000 if resp.elapsed else None,
                "headers": dict(resp.headers),
            }
    except httpx.ConnectError:
        return {"url": url, "healthy": False, "error": "Connection refused"}
    except httpx.TimeoutException:
        return {"url": url, "healthy": False, "error": "Request timed out"}
    except Exception as e:
        return {"url": url, "healthy": False, "error": str(e)}
