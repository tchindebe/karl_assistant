"""
Gestion de la configuration Nginx.
Génère les configs, les teste, recharge nginx.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

NGINX_SITES_DIR = Path(os.getenv("NGINX_SITES_DIR", "/etc/nginx/sites-enabled"))
TEMPLATES_DIR = Path(__file__).parent / "nginx_templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(disabled_extensions=("j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
)


async def _run(cmd: str) -> Dict[str, Any]:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode(errors="replace").strip(),
        "stderr": stderr.decode(errors="replace").strip(),
    }


class NginxManager:

    def _get_template_name(self, ssl: bool, websocket: bool) -> str:
        if ssl and websocket:
            return "https_ws.conf.j2"
        elif ssl:
            return "https.conf.j2"
        elif websocket:
            return "http_ws.conf.j2"
        return "http.conf.j2"

    async def configure(
        self,
        domain: str,
        upstream_port: int,
        ssl: bool = False,
        websocket: bool = False,
        upstream_host: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        template_name = self._get_template_name(ssl, websocket)
        try:
            template = jinja_env.get_template(template_name)
        except Exception:
            # Fallback: generate config inline
            template = None

        if template:
            config_content = template.render(
                domain=domain,
                upstream_host=upstream_host,
                upstream_port=upstream_port,
                ssl=ssl,
                websocket=websocket,
            )
        else:
            config_content = self._generate_inline(
                domain, upstream_host, upstream_port, ssl, websocket
            )

        # Écrire la config
        NGINX_SITES_DIR.mkdir(parents=True, exist_ok=True)
        config_file = NGINX_SITES_DIR / f"{domain}.conf"
        config_file.write_text(config_content, encoding="utf-8")

        # Tester la config
        test_result = await _run("nginx -t")
        if test_result["returncode"] != 0:
            config_file.unlink(missing_ok=True)
            return {
                "success": False,
                "domain": domain,
                "error": f"Nginx config test failed: {test_result['stderr']}",
            }

        # Recharger nginx
        reload_result = await _run("systemctl reload nginx || nginx -s reload")

        return {
            "success": True,
            "domain": domain,
            "config_file": str(config_file),
            "ssl": ssl,
            "websocket": websocket,
            "reload_output": reload_result["stdout"] or reload_result["stderr"],
        }

    def _generate_inline(
        self,
        domain: str,
        upstream_host: str,
        upstream_port: int,
        ssl: bool,
        websocket: bool,
    ) -> str:
        ws_headers = ""
        if websocket:
            ws_headers = """
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";"""

        if ssl:
            return f"""server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {{
        proxy_pass http://{upstream_host}:{upstream_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;{ws_headers}
    }}
}}
"""
        else:
            return f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://{upstream_host}:{upstream_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;{ws_headers}
    }}
}}
"""

    async def remove_config(self, domain: str) -> Dict[str, Any]:
        config_file = NGINX_SITES_DIR / f"{domain}.conf"
        if config_file.exists():
            config_file.unlink()
            reload_result = await _run("systemctl reload nginx || nginx -s reload")
            return {
                "success": True,
                "domain": domain,
                "message": "Config removed and nginx reloaded",
            }
        return {"success": False, "domain": domain, "error": "Config file not found"}

    async def list_configs(self) -> Dict[str, Any]:
        configs = []
        if NGINX_SITES_DIR.exists():
            for f in NGINX_SITES_DIR.iterdir():
                if f.suffix == ".conf":
                    configs.append({
                        "domain": f.stem,
                        "file": str(f),
                        "size": f.stat().st_size,
                    })
        return {"configs": configs}

    async def reload(self) -> Dict[str, Any]:
        test_result = await _run("nginx -t")
        if test_result["returncode"] != 0:
            return {"success": False, "error": test_result["stderr"]}

        reload_result = await _run("systemctl reload nginx || nginx -s reload")
        return {
            "success": reload_result["returncode"] == 0,
            "output": reload_result["stdout"] or reload_result["stderr"],
        }
