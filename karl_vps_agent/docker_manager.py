"""
Gestion Docker Compose et containers.
"""
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

APPS_BASE_DIR = Path(os.getenv("APPS_BASE_DIR", "/opt/karl/deployments"))


def _sanitize_name(name: str) -> str:
    """Sanitise un nom d'app (alphanumérique + tirets uniquement)."""
    clean = re.sub(r"[^a-zA-Z0-9\-]", "-", name).strip("-").lower()
    if not clean:
        raise ValueError(f"Invalid app name: {name!r}")
    return clean


async def _run(cmd: str, cwd: Optional[Path] = None) -> Dict[str, Any]:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
    )
    stdout, stderr = await proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode(errors="replace").strip(),
        "stderr": stderr.decode(errors="replace").strip(),
    }


class DockerManager:

    async def deploy(
        self,
        name: str,
        compose_content: str,
        env_vars: Dict[str, str] = {},
        pull: bool = True,
    ) -> Dict[str, Any]:
        name = _sanitize_name(name)
        app_dir = APPS_BASE_DIR / name
        app_dir.mkdir(parents=True, exist_ok=True)

        # Écrire docker-compose.yml
        compose_file = app_dir / "docker-compose.yml"
        compose_file.write_text(compose_content, encoding="utf-8")

        # Écrire .env si fourni
        if env_vars:
            env_file = app_dir / ".env"
            env_content = "\n".join(f"{k}={v}" for k, v in env_vars.items())
            env_file.write_text(env_content, encoding="utf-8")

        # Pull les images si demandé
        if pull:
            await _run("docker compose pull", cwd=app_dir)

        # Démarrer
        up_result = await _run("docker compose up -d --remove-orphans", cwd=app_dir)

        if up_result["returncode"] != 0:
            return {
                "success": False,
                "name": name,
                "error": up_result["stderr"] or up_result["stdout"],
            }

        # Récupérer le statut
        ps_result = await _run("docker compose ps --format json", cwd=app_dir)

        return {
            "success": True,
            "name": name,
            "app_dir": str(app_dir),
            "output": up_result["stdout"],
            "ps": ps_result["stdout"],
        }

    async def list_deployments(self) -> Dict[str, Any]:
        deployments = []
        if not APPS_BASE_DIR.exists():
            return {"deployments": []}

        for app_dir in APPS_BASE_DIR.iterdir():
            if not app_dir.is_dir():
                continue
            compose_file = app_dir / "docker-compose.yml"
            if not compose_file.exists():
                continue

            ps_result = await _run("docker compose ps --format json", cwd=app_dir)
            deployments.append({
                "name": app_dir.name,
                "path": str(app_dir),
                "compose_exists": True,
                "ps_output": ps_result["stdout"],
            })

        return {"success": True, "deployments": deployments}

    async def list_containers(self) -> Dict[str, Any]:
        result = await _run(
            'docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"'
        )
        containers = []
        for line in result["stdout"].splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                containers.append({
                    "name": parts[0],
                    "image": parts[1],
                    "status": parts[2],
                    "ports": parts[3] if len(parts) > 3 else "",
                })
        return {"success": True, "containers": containers}

    async def manage_container(self, name: str, action: str) -> Dict[str, Any]:
        name = _sanitize_name(name)
        cmd_map = {
            "start": f"docker start {name}",
            "stop": f"docker stop {name}",
            "restart": f"docker restart {name}",
            "remove": f"docker rm -f {name}",
            "pause": f"docker pause {name}",
            "unpause": f"docker unpause {name}",
        }
        cmd = cmd_map[action]
        result = await _run(cmd)
        return {
            "success": result["returncode"] == 0,
            "name": name,
            "action": action,
            "output": result["stdout"] or result["stderr"],
        }

    async def get_logs(
        self, service: str, lines: int = 100, since: Optional[str] = None
    ) -> Dict[str, Any]:
        service = _sanitize_name(service)
        since_flag = f"--since {since}" if since else ""
        cmd = f"docker logs --tail {lines} {since_flag} {service} 2>&1"
        result = await _run(cmd)
        return {
            "service": service,
            "lines": lines,
            "logs": result["stdout"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def deploy_from_git(
        self,
        repo_url: str,
        branch: str,
        app_name: str,
        environment: str = "production",
    ) -> Dict[str, Any]:
        """
        Clone/pull un repo Git et lance docker-compose.
        Le repo doit contenir un docker-compose.yml à la racine ou dans un sous-dossier.
        """
        app_name = _sanitize_name(app_name)
        app_dir = APPS_BASE_DIR / app_name

        # Vérifier que l'URL est safe (pas d'injection de commande)
        import urllib.parse
        parsed = urllib.parse.urlparse(repo_url)
        if parsed.scheme not in ("https", "http", "git", "ssh"):
            return {"success": False, "error": f"Schéma URL non autorisé: {parsed.scheme}"}

        try:
            if app_dir.exists() and (app_dir / ".git").exists():
                # Repo existant → pull
                fetch_result = await _run(
                    f"git fetch origin {branch} && git reset --hard origin/{branch}",
                    cwd=app_dir,
                )
                action = "pull"
            else:
                # Premier déploiement → clone
                app_dir.mkdir(parents=True, exist_ok=True)
                fetch_result = await _run(
                    f"git clone --branch {branch} --single-branch {repo_url} .",
                    cwd=app_dir,
                )
                action = "clone"

            if fetch_result["returncode"] != 0:
                return {
                    "success": False,
                    "action": action,
                    "error": fetch_result["stderr"] or fetch_result["stdout"],
                }

            # Chercher le docker-compose.yml
            compose_candidates = [
                app_dir / "docker-compose.yml",
                app_dir / f"docker-compose.{environment}.yml",
                app_dir / "compose.yml",
            ]
            compose_file = None
            for candidate in compose_candidates:
                if candidate.exists():
                    compose_file = candidate
                    break

            if not compose_file:
                return {
                    "success": False,
                    "error": "Aucun docker-compose.yml trouvé dans le repo",
                }

            compose_cwd = compose_file.parent

            # Déployer
            await _run("docker compose pull", cwd=compose_cwd)
            up_result = await _run(
                "docker compose up -d --remove-orphans --build",
                cwd=compose_cwd,
            )

            # Info du commit
            commit_result = await _run("git log -1 --format='%h %s'", cwd=app_dir)
            commit_info = commit_result["stdout"].strip("'")

            return {
                "success": up_result["returncode"] == 0,
                "app_name": app_name,
                "action": action,
                "branch": branch,
                "environment": environment,
                "commit": commit_info,
                "compose_file": str(compose_file),
                "output": up_result["stdout"] or up_result["stderr"],
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
