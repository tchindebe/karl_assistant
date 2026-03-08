"""
Karl VPS Agent — Daemon léger qui tourne sur le VPS.
Sécurisé par Bearer token. Expose les opérations Docker, Nginx, SSL, métriques,
sauvegardes, pare-feu, bases de données, sécurité, CI/CD.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv

from system_metrics import get_metrics
from docker_manager import DockerManager
from nginx_manager import NginxManager
from ssl_manager import SSLManager
from backup_manager import (
    backup_docker_volumes, backup_database, backup_configs,
    list_backups, restore_volume_backup, cleanup_old_backups, upload_to_s3,
)
from firewall_manager import FirewallManager
from database_manager import DatabaseManager
from security_auditor import SecurityAuditor

load_dotenv()

API_KEY = os.getenv("KARL_AGENT_API_KEY", "")
if not API_KEY:
    raise RuntimeError("KARL_AGENT_API_KEY env var is required")

docker_mgr = DockerManager()
nginx_mgr = NginxManager()
ssl_mgr = SSLManager()
fw_mgr = FirewallManager()
db_mgr = DatabaseManager()
sec_auditor = SecurityAuditor()

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Karl VPS Agent starting...")
    yield
    print("Karl VPS Agent stopped.")


app = FastAPI(title="Karl VPS Agent", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "karl-vps-agent", "version": "2.0.0"}


# ─── Métriques système ─────────────────────────────────────────────────────────

@app.get("/metrics", dependencies=[Depends(verify_token)])
async def metrics():
    return get_metrics()


# ─── Déploiement ───────────────────────────────────────────────────────────────

class DeployRequest(BaseModel):
    name: str
    compose_content: str
    env_vars: Dict[str, str] = {}
    pull: bool = True
    environment: str = "production"  # production | staging | dev


@app.post("/deploy", dependencies=[Depends(verify_token)])
async def deploy(req: DeployRequest):
    result = await docker_mgr.deploy(
        name=req.name,
        compose_content=req.compose_content,
        env_vars=req.env_vars,
        pull=req.pull,
        environment=req.environment,
    )
    return result


@app.get("/deployments", dependencies=[Depends(verify_token)])
async def list_deployments():
    return await docker_mgr.list_deployments()


# ─── Containers ────────────────────────────────────────────────────────────────

@app.get("/containers", dependencies=[Depends(verify_token)])
async def list_containers():
    return await docker_mgr.list_containers()


@app.post("/containers/{name}/{action}", dependencies=[Depends(verify_token)])
async def manage_container(name: str, action: str):
    allowed = {"start", "stop", "restart", "remove", "pause", "unpause"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"Action must be one of {allowed}")
    return await docker_mgr.manage_container(name, action)


@app.get("/logs/{service}", dependencies=[Depends(verify_token)])
async def get_logs(service: str, lines: int = 100, since: Optional[str] = None):
    return await docker_mgr.get_logs(service, lines, since)


# ─── CI/CD — Deploy from Git ───────────────────────────────────────────────────

class GitDeployRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    app_name: str
    environment: str = "production"
    build_command: str = ""
    compose_file: str = "docker-compose.yml"
    env_vars: Dict[str, str] = {}


@app.post("/deploy/git", dependencies=[Depends(verify_token)])
async def deploy_from_git(req: GitDeployRequest):
    result = await docker_mgr.deploy_from_git(
        repo_url=req.repo_url,
        branch=req.branch,
        app_name=req.app_name,
        environment=req.environment,
        build_command=req.build_command,
        compose_file=req.compose_file,
        env_vars=req.env_vars,
    )
    return result


# ─── Nginx ─────────────────────────────────────────────────────────────────────

class NginxConfigRequest(BaseModel):
    domain: str
    upstream_port: int
    ssl: bool = False
    websocket: bool = False
    upstream_host: str = "127.0.0.1"


@app.post("/nginx/configure", dependencies=[Depends(verify_token)])
async def nginx_configure(req: NginxConfigRequest):
    return await nginx_mgr.configure(
        domain=req.domain,
        upstream_port=req.upstream_port,
        ssl=req.ssl,
        websocket=req.websocket,
        upstream_host=req.upstream_host,
    )


@app.delete("/nginx/{domain}", dependencies=[Depends(verify_token)])
async def nginx_remove(domain: str):
    return await nginx_mgr.remove_config(domain)


@app.get("/nginx", dependencies=[Depends(verify_token)])
async def nginx_list():
    return await nginx_mgr.list_configs()


@app.post("/nginx/reload", dependencies=[Depends(verify_token)])
async def nginx_reload():
    return await nginx_mgr.reload()


# ─── SSL ───────────────────────────────────────────────────────────────────────

class SSLRequest(BaseModel):
    domain: str
    email: str


@app.post("/ssl/enable", dependencies=[Depends(verify_token)])
async def ssl_enable(req: SSLRequest):
    return await ssl_mgr.enable(req.domain, req.email)


@app.post("/ssl/renew", dependencies=[Depends(verify_token)])
async def ssl_renew():
    return await ssl_mgr.renew_all()


@app.get("/ssl", dependencies=[Depends(verify_token)])
async def ssl_list():
    return await ssl_mgr.list_certs()


@app.get("/ssl/expiry", dependencies=[Depends(verify_token)])
async def ssl_expiry():
    """Retourne les dates d'expiration de tous les certificats."""
    return await ssl_mgr.get_expiry_info()


@app.get("/ssl/check-domain", dependencies=[Depends(verify_token)])
async def ssl_check_domain(domain: str, port: int = 443):
    """Vérifie le certificat SSL d'un domaine depuis l'extérieur."""
    return await ssl_mgr.check_domain_ssl(domain, port)


class SSLDomainRequest(BaseModel):
    domain: str


@app.post("/ssl/force-renew", dependencies=[Depends(verify_token)])
async def ssl_force_renew(req: SSLDomainRequest):
    """Force le renouvellement d'un certificat spécifique."""
    return await ssl_mgr.force_renew(req.domain)


@app.post("/ssl/revoke", dependencies=[Depends(verify_token)])
async def ssl_revoke(req: SSLDomainRequest):
    """Révoque et supprime un certificat SSL."""
    return await ssl_mgr.revoke(req.domain)


# ─── Sauvegardes ───────────────────────────────────────────────────────────────

class BackupRequest(BaseModel):
    type: str = "all"   # all | volumes | database | configs
    app_name: Optional[str] = None
    db_type: Optional[str] = None          # postgresql | mysql | mongodb | sqlite
    container_name: Optional[str] = None
    database_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    upload_s3: bool = False
    s3_bucket: Optional[str] = None


@app.post("/backup", dependencies=[Depends(verify_token)])
async def create_backup(req: BackupRequest):
    results = {}
    if req.type in ("all", "volumes"):
        results["volumes"] = backup_docker_volumes(req.app_name)
    if req.type == "database" and req.container_name and req.database_name:
        results["database"] = backup_database(
            req.db_type or "postgresql",
            req.container_name,
            req.database_name,
            req.db_user or "",
            req.db_password or "",
        )
    if req.type in ("all", "configs"):
        results["configs"] = backup_configs()

    if req.upload_s3 and req.s3_bucket:
        for btype, res in results.items():
            if res.get("success") and res.get("file"):
                results[f"{btype}_s3"] = upload_to_s3(res["file"], req.s3_bucket)

    return results


@app.get("/backups", dependencies=[Depends(verify_token)])
async def get_backups(type: str = "all"):
    return list_backups(type)


class RestoreRequest(BaseModel):
    backup_file: str
    volume_name: str


@app.post("/backup/restore", dependencies=[Depends(verify_token)])
async def restore_backup(req: RestoreRequest):
    return restore_volume_backup(req.backup_file, req.volume_name)


@app.delete("/backups/cleanup", dependencies=[Depends(verify_token)])
async def cleanup_backups(keep_days: int = 14):
    return cleanup_old_backups(keep_days)


# ─── Pare-feu (UFW) ────────────────────────────────────────────────────────────

class FirewallRuleRequest(BaseModel):
    action: str          # allow | deny | limit
    port: Optional[int] = None
    proto: str = "tcp"   # tcp | udp | any
    from_ip: Optional[str] = None
    comment: Optional[str] = None


@app.get("/firewall/rules", dependencies=[Depends(verify_token)])
async def firewall_rules():
    return fw_mgr.list_rules()


@app.post("/firewall/rules", dependencies=[Depends(verify_token)])
async def firewall_add(req: FirewallRuleRequest):
    return fw_mgr.add_rule(req.action, req.port, req.proto, req.from_ip, req.comment)


@app.delete("/firewall/rules", dependencies=[Depends(verify_token)])
async def firewall_remove(port: Optional[int] = None, from_ip: Optional[str] = None):
    return fw_mgr.remove_rule(port, from_ip)


@app.post("/firewall/block-ip", dependencies=[Depends(verify_token)])
async def firewall_block(ip: str, comment: Optional[str] = None):
    return fw_mgr.block_ip(ip, comment)


@app.get("/firewall/status", dependencies=[Depends(verify_token)])
async def firewall_status():
    return fw_mgr.get_status()


@app.get("/firewall/brute-force", dependencies=[Depends(verify_token)])
async def firewall_brute_force():
    """Détecte les IPs qui font du brute force SSH."""
    return fw_mgr.detect_brute_force()


# ─── Bases de données ──────────────────────────────────────────────────────────

class DBDumpRequest(BaseModel):
    db_type: str
    container_name: str
    database_name: str
    db_user: str = ""
    db_password: str = ""


@app.post("/database/dump", dependencies=[Depends(verify_token)])
async def database_dump(req: DBDumpRequest):
    return await db_mgr.dump(req.db_type, req.container_name, req.database_name, req.db_user, req.db_password)


class DBRestoreRequest(BaseModel):
    db_type: str
    container_name: str
    database_name: str
    backup_file: str
    db_user: str = ""
    db_password: str = ""


@app.post("/database/restore", dependencies=[Depends(verify_token)])
async def database_restore(req: DBRestoreRequest):
    return await db_mgr.restore(req.db_type, req.container_name, req.database_name, req.backup_file, req.db_user, req.db_password)


@app.get("/database/list", dependencies=[Depends(verify_token)])
async def database_list(container: str, db_type: str):
    return await db_mgr.list_databases(container, db_type)


@app.get("/database/stats/{container_name}", dependencies=[Depends(verify_token)])
async def database_stats(container_name: str, db_type: str):
    return await db_mgr.get_stats(container_name, db_type)


@app.get("/database/connections/{container_name}", dependencies=[Depends(verify_token)])
async def database_connections(container_name: str, db_type: str):
    return await db_mgr.get_connections(container_name, db_type)


@app.get("/database/size/{container_name}", dependencies=[Depends(verify_token)])
async def database_size(container_name: str, db_type: str, db_name: str):
    return await db_mgr.get_database_size(container_name, db_type, db_name)


@app.get("/database/slow-queries/{container_name}", dependencies=[Depends(verify_token)])
async def slow_queries(container_name: str, db_type: str = "postgresql", threshold_ms: int = 1000):
    return await db_mgr.get_slow_queries(container_name, db_type, threshold_ms)


class DBQueryRequest(BaseModel):
    container: str
    db_type: str
    db_name: str
    query: str
    user: str = "postgres"


@app.post("/database/query", dependencies=[Depends(verify_token)])
async def database_query(req: DBQueryRequest):
    return await db_mgr.execute_query(req.container, req.db_type, req.db_name, req.query, req.user)


class DBOptimizeRequest(BaseModel):
    container: str
    db_type: str
    db_name: str


@app.post("/database/optimize", dependencies=[Depends(verify_token)])
async def database_optimize(req: DBOptimizeRequest):
    return await db_mgr.optimize_database(req.container, req.db_type, req.db_name)


# ─── Audit sécurité ────────────────────────────────────────────────────────────

@app.get("/security/audit", dependencies=[Depends(verify_token)])
async def security_audit():
    return await sec_auditor.full_audit()


@app.get("/security/open-ports", dependencies=[Depends(verify_token)])
async def security_ports():
    return await sec_auditor.check_open_ports()


@app.get("/security/docker-images", dependencies=[Depends(verify_token)])
async def security_images():
    return await sec_auditor.check_docker_images()


@app.get("/security/file-permissions", dependencies=[Depends(verify_token)])
async def security_files():
    return await sec_auditor.check_file_permissions()


@app.get("/security/ssh-config", dependencies=[Depends(verify_token)])
async def security_ssh_config():
    return await sec_auditor.check_ssh_config()


@app.get("/security/failed-logins", dependencies=[Depends(verify_token)])
async def security_failed_logins(hours: int = 24):
    return await sec_auditor.check_failed_logins(hours)


@app.get("/security/system-updates", dependencies=[Depends(verify_token)])
async def security_system_updates():
    return await sec_auditor.check_system_updates()


@app.post("/security/harden-ssh", dependencies=[Depends(verify_token)])
async def security_harden_ssh():
    return await sec_auditor.harden_ssh()


@app.post("/security/install-fail2ban", dependencies=[Depends(verify_token)])
async def security_install_fail2ban():
    return await sec_auditor.install_fail2ban()


@app.get("/security/malware-scan", dependencies=[Depends(verify_token)])
async def security_malware_scan():
    return await sec_auditor.scan_malware()


# ─── Système ───────────────────────────────────────────────────────────────────

async def _run_shell(cmd: str) -> Dict[str, Any]:
    import asyncio as _asyncio
    proc = await _asyncio.create_subprocess_shell(
        cmd,
        stdout=_asyncio.subprocess.PIPE,
        stderr=_asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode(errors="replace").strip(),
        "stderr": stderr.decode(errors="replace").strip(),
    }


@app.post("/system/docker-prune", dependencies=[Depends(verify_token)])
async def system_docker_prune():
    """Nettoie les images, conteneurs arrêtés, volumes et réseaux inutilisés."""
    result = await _run_shell("docker system prune -f --volumes")
    return {
        "success": result["returncode"] == 0,
        "output": result["stdout"],
        "error": result["stderr"] if result["returncode"] != 0 else None,
    }


@app.get("/system/disk-breakdown", dependencies=[Depends(verify_token)])
async def system_disk_breakdown():
    """Analyse l'utilisation disque par répertoire clé."""
    dirs = ["/opt/karl", "/var/lib/docker", "/var/log", "/home", "/tmp", "/backups"]
    breakdown = {}
    for d in dirs:
        r = await _run_shell(f"du -sh {d} 2>/dev/null || echo '0\t{d}'")
        if r["stdout"]:
            parts = r["stdout"].split("\t", 1)
            breakdown[d] = parts[0] if len(parts) == 2 else r["stdout"]
    total = await _run_shell("df -h / | tail -1")
    return {"success": True, "breakdown": breakdown, "root_fs": total["stdout"]}


# ─── Limites conteneurs ────────────────────────────────────────────────────────

class ContainerLimitsRequest(BaseModel):
    app_name: str
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None


@app.post("/containers/limits", dependencies=[Depends(verify_token)])
async def set_container_limits(req: ContainerLimitsRequest):
    """Applique des limites CPU/RAM à un conteneur via docker update."""
    args = ["docker", "update"]
    if req.cpu_limit:
        args += ["--cpus", req.cpu_limit]
    if req.memory_limit:
        args += ["--memory", req.memory_limit]
    args.append(req.app_name)

    import asyncio as _asyncio
    proc = await _asyncio.create_subprocess_exec(
        *args,
        stdout=_asyncio.subprocess.PIPE,
        stderr=_asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "success": proc.returncode == 0,
        "container": req.app_name,
        "output": stdout.decode().strip(),
        "error": stderr.decode().strip() if proc.returncode != 0 else None,
    }


if __name__ == "__main__":
    port = int(os.getenv("KARL_AGENT_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
