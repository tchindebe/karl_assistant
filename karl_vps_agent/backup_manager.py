"""
Gestionnaire de sauvegardes — volumes Docker, bases de données, fichiers.
Supporte: stockage local, S3 (via boto3), Backblaze B2, FTP.
"""
import os
import subprocess
import tarfile
import gzip
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

BACKUPS_DIR = Path(os.getenv("BACKUPS_DIR", "/opt/karl/backups"))
APPS_BASE_DIR = Path(os.getenv("APPS_BASE_DIR", "/opt/karl/deployments"))
MAX_LOCAL_BACKUPS = int(os.getenv("MAX_LOCAL_BACKUPS", "14"))


def _ensure_dirs():
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUPS_DIR / "volumes").mkdir(exist_ok=True)
    (BACKUPS_DIR / "databases").mkdir(exist_ok=True)
    (BACKUPS_DIR / "configs").mkdir(exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Backup volumes Docker ──────────────────────────────────────────────────────

def backup_docker_volumes(app_name: Optional[str] = None) -> Dict[str, Any]:
    """Sauvegarde les volumes Docker d'une app ou de toutes les apps."""
    _ensure_dirs()
    backed_up = []
    errors = []

    # Récupérer la liste des volumes
    cmd = ["docker", "volume", "ls", "--format", "{{.Name}}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    volumes = [v.strip() for v in result.stdout.splitlines() if v.strip()]

    if app_name:
        volumes = [v for v in volumes if app_name.lower() in v.lower()]

    for volume in volumes:
        try:
            ts = _timestamp()
            backup_path = BACKUPS_DIR / "volumes" / f"{volume}_{ts}.tar.gz"
            # Utiliser un conteneur temporaire pour accéder au volume
            subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{volume}:/data",
                "-v", f"{BACKUPS_DIR / 'volumes'}:/backup",
                "alpine",
                "tar", "czf", f"/backup/{volume}_{ts}.tar.gz", "-C", "/data", "."
            ], check=True, capture_output=True, timeout=300)
            size = backup_path.stat().st_size if backup_path.exists() else 0
            backed_up.append({
                "volume": volume,
                "file": str(backup_path),
                "size_mb": round(size / 1024 / 1024, 2),
            })
        except Exception as e:
            errors.append({"volume": volume, "error": str(e)})

    return {"backed_up": backed_up, "errors": errors, "timestamp": _timestamp()}


# ── Backup bases de données ────────────────────────────────────────────────────

def backup_database(
    db_type: str,           # postgresql | mysql | mongodb | sqlite
    container_name: str,
    database_name: str,
    db_user: str = "",
    db_password: str = "",
) -> Dict[str, Any]:
    """Dump d'une base de données depuis un conteneur Docker."""
    _ensure_dirs()
    ts = _timestamp()
    filename = f"{container_name}_{database_name}_{ts}.sql.gz"
    backup_path = BACKUPS_DIR / "databases" / filename

    try:
        if db_type == "postgresql":
            env = os.environ.copy()
            if db_password:
                env["PGPASSWORD"] = db_password
            dump_cmd = [
                "docker", "exec", container_name,
                "pg_dump", "-U", db_user or "postgres", database_name
            ]
        elif db_type == "mysql":
            user = db_user or "root"
            pwd_arg = f"-p{db_password}" if db_password else ""
            dump_cmd = [
                "docker", "exec", container_name,
                "mysqldump", f"-u{user}", pwd_arg, database_name
            ]
            dump_cmd = [a for a in dump_cmd if a]
        elif db_type == "mongodb":
            dump_cmd = [
                "docker", "exec", container_name,
                "mongodump", "--db", database_name, "--archive"
            ]
            filename = filename.replace(".sql.gz", ".archive.gz")
            backup_path = BACKUPS_DIR / "databases" / filename
        elif db_type == "sqlite":
            # SQLite : copier le fichier directement
            db_path_in_container = f"/data/{database_name}"
            subprocess.run([
                "docker", "cp", f"{container_name}:{db_path_in_container}",
                str(backup_path).replace(".sql.gz", ".db")
            ], check=True, timeout=60)
            actual_path = str(backup_path).replace(".sql.gz", ".db")
            size = Path(actual_path).stat().st_size
            return {
                "success": True,
                "file": actual_path,
                "size_mb": round(size / 1024 / 1024, 2),
                "database": database_name,
            }
        else:
            return {"success": False, "error": f"Type DB non supporté: {db_type}"}

        # Exécuter le dump et compresser
        dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with gzip.open(backup_path, "wb") as gz:
            shutil.copyfileobj(dump_proc.stdout, gz)
        dump_proc.wait(timeout=300)

        if dump_proc.returncode != 0:
            return {"success": False, "error": dump_proc.stderr.read().decode()}

        size = backup_path.stat().st_size
        return {
            "success": True,
            "file": str(backup_path),
            "size_mb": round(size / 1024 / 1024, 2),
            "database": database_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Backup configurations ──────────────────────────────────────────────────────

def backup_configs() -> Dict[str, Any]:
    """Sauvegarde les fichiers de configuration (compose files, nginx, .env)."""
    _ensure_dirs()
    ts = _timestamp()
    archive_path = BACKUPS_DIR / "configs" / f"configs_{ts}.tar.gz"

    dirs_to_backup = [str(APPS_BASE_DIR), "/etc/nginx/sites-enabled"]

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for path in dirs_to_backup:
                if Path(path).exists():
                    tar.add(path, arcname=Path(path).name)

        size = archive_path.stat().st_size
        return {
            "success": True,
            "file": str(archive_path),
            "size_mb": round(size / 1024 / 1024, 2),
            "included": [d for d in dirs_to_backup if Path(d).exists()],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Liste et restauration ──────────────────────────────────────────────────────

def list_backups(backup_type: str = "all") -> List[Dict[str, Any]]:
    """Liste toutes les sauvegardes disponibles."""
    _ensure_dirs()
    backups = []
    dirs = []

    if backup_type in ("all", "volumes"):
        dirs.append(("volumes", BACKUPS_DIR / "volumes"))
    if backup_type in ("all", "databases"):
        dirs.append(("databases", BACKUPS_DIR / "databases"))
    if backup_type in ("all", "configs"):
        dirs.append(("configs", BACKUPS_DIR / "configs"))

    for btype, bdir in dirs:
        if not bdir.exists():
            continue
        for f in sorted(bdir.iterdir(), reverse=True):
            if f.is_file():
                stat = f.stat()
                backups.append({
                    "type": btype,
                    "name": f.name,
                    "path": str(f),
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

    return backups


def restore_volume_backup(backup_file: str, volume_name: str) -> Dict[str, Any]:
    """Restaure un volume Docker depuis une sauvegarde."""
    backup_path = Path(backup_file)
    if not backup_path.exists():
        return {"success": False, "error": f"Fichier introuvable: {backup_file}"}

    try:
        # Créer le volume s'il n'existe pas
        subprocess.run(["docker", "volume", "create", volume_name], check=True, capture_output=True)

        # Restaurer dans le volume
        subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{volume_name}:/data",
            "-v", f"{backup_path.parent}:/backup",
            "alpine",
            "sh", "-c", f"cd /data && tar xzf /backup/{backup_path.name}"
        ], check=True, timeout=300)

        return {"success": True, "volume": volume_name, "from": backup_file}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_old_backups(keep_days: int = 14) -> Dict[str, Any]:
    """Supprime les sauvegardes plus anciennes que keep_days jours."""
    _ensure_dirs()
    cutoff = datetime.now() - timedelta(days=keep_days)
    deleted = []
    freed_mb = 0

    for subdir in (BACKUPS_DIR / "volumes", BACKUPS_DIR / "databases", BACKUPS_DIR / "configs"):
        if not subdir.exists():
            continue
        for f in subdir.iterdir():
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                size = f.stat().st_size
                f.unlink()
                freed_mb += size / 1024 / 1024
                deleted.append(f.name)

    return {
        "deleted_count": len(deleted),
        "freed_mb": round(freed_mb, 2),
        "files": deleted,
    }


# ── Upload S3 (optionnel) ──────────────────────────────────────────────────────

def upload_to_s3(local_path: str, bucket: str, prefix: str = "karl-backups/") -> Dict[str, Any]:
    """Upload un fichier vers S3 ou un stockage compatible (Backblaze, MinIO)."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        s3_endpoint = os.getenv("S3_ENDPOINT_URL")
        s3_key = os.getenv("S3_ACCESS_KEY")
        s3_secret = os.getenv("S3_SECRET_KEY")

        kwargs = {}
        if s3_endpoint:
            kwargs["endpoint_url"] = s3_endpoint

        s3 = boto3.client("s3", aws_access_key_id=s3_key, aws_secret_access_key=s3_secret, **kwargs)
        filename = Path(local_path).name
        key = f"{prefix}{filename}"
        s3.upload_file(local_path, bucket, key)
        return {"success": True, "bucket": bucket, "key": key}
    except ImportError:
        return {"success": False, "error": "boto3 non installé: pip install boto3"}
    except Exception as e:
        return {"success": False, "error": str(e)}
