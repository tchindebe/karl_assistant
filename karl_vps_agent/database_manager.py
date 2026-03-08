"""
Gestionnaire de bases de données — PostgreSQL, MySQL, MongoDB, Redis.
Permet à Karl d'interagir avec les BDD tournant dans des conteneurs Docker.
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("karl.database")


class DatabaseManager:
    """Gère les opérations sur les bases de données dans les conteneurs Docker."""

    # ── Informations de connexion ──────────────────────────────────────────────

    async def list_databases(self, container: str, db_type: str) -> Dict[str, Any]:
        """Liste les bases de données dans un conteneur."""
        try:
            if db_type == "postgresql":
                cmd = ["docker", "exec", container, "psql", "-U", "postgres",
                       "-t", "-c", "SELECT datname FROM pg_database WHERE datistemplate = false;"]
            elif db_type == "mysql":
                cmd = ["docker", "exec", container, "mysql", "-u", "root",
                       "-e", "SHOW DATABASES;"]
            elif db_type == "mongodb":
                cmd = ["docker", "exec", container, "mongo", "--quiet",
                       "--eval", "db.adminCommand('listDatabases').databases.map(d => d.name).join('\\n')"]
            elif db_type == "redis":
                cmd = ["docker", "exec", container, "redis-cli", "INFO", "keyspace"]
            else:
                return {"success": False, "error": f"Type de BDD non supporté: {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode().strip()}

            databases = [line.strip() for line in stdout.decode().splitlines() if line.strip()]
            return {"success": True, "databases": databases, "db_type": db_type, "container": container}

        except Exception as e:
            logger.error(f"list_databases error: {e}")
            return {"success": False, "error": str(e)}

    async def get_database_size(self, container: str, db_type: str, db_name: str) -> Dict[str, Any]:
        """Retourne la taille d'une base de données."""
        try:
            if db_type == "postgresql":
                cmd = ["docker", "exec", container, "psql", "-U", "postgres",
                       "-t", "-c", f"SELECT pg_size_pretty(pg_database_size('{db_name}'));"]
            elif db_type == "mysql":
                query = (f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' "
                         f"FROM information_schema.tables WHERE table_schema = '{db_name}';")
                cmd = ["docker", "exec", container, "mysql", "-u", "root", "-e", query]
            else:
                return {"success": False, "error": f"Taille non disponible pour {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode().strip()}

            size = stdout.decode().strip()
            return {"success": True, "database": db_name, "size": size}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_connections(self, container: str, db_type: str) -> Dict[str, Any]:
        """Retourne les connexions actives."""
        try:
            if db_type == "postgresql":
                cmd = ["docker", "exec", container, "psql", "-U", "postgres", "-c",
                       "SELECT pid, usename, application_name, state, query_start, "
                       "LEFT(query, 80) AS query FROM pg_stat_activity WHERE state != 'idle' LIMIT 20;"]
            elif db_type == "mysql":
                cmd = ["docker", "exec", container, "mysql", "-u", "root",
                       "-e", "SHOW PROCESSLIST;"]
            elif db_type == "redis":
                cmd = ["docker", "exec", container, "redis-cli", "CLIENT", "LIST"]
            else:
                return {"success": False, "error": f"Connexions non disponibles pour {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode().strip()}

            return {"success": True, "connections": stdout.decode().strip()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_slow_queries(self, container: str, db_type: str, threshold_ms: int = 1000) -> Dict[str, Any]:
        """Récupère les requêtes lentes."""
        try:
            if db_type == "postgresql":
                cmd = ["docker", "exec", container, "psql", "-U", "postgres", "-c",
                       f"SELECT pid, now() - query_start AS duration, usename, "
                       f"LEFT(query, 200) AS query FROM pg_stat_activity "
                       f"WHERE state != 'idle' AND now() - query_start > interval '{threshold_ms} milliseconds' "
                       f"ORDER BY duration DESC LIMIT 10;"]
            elif db_type == "mysql":
                cmd = ["docker", "exec", container, "mysql", "-u", "root", "-e",
                       f"SELECT * FROM information_schema.processlist "
                       f"WHERE TIME > {threshold_ms // 1000} ORDER BY TIME DESC LIMIT 10;"]
            else:
                return {"success": False, "error": f"Requêtes lentes non disponibles pour {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode().strip()}

            output = stdout.decode().strip()
            return {
                "success": True,
                "slow_queries": output,
                "threshold_ms": threshold_ms,
                "db_type": db_type,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_query(
        self,
        container: str,
        db_type: str,
        db_name: str,
        query: str,
        user: str = "postgres",
    ) -> Dict[str, Any]:
        """Exécute une requête SQL (SELECT uniquement pour la sécurité)."""
        # Sécurité: interdire les requêtes destructives
        query_upper = query.upper().strip()
        dangerous = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE", "GRANT", "REVOKE"]
        for keyword in dangerous:
            if query_upper.startswith(keyword):
                return {
                    "success": False,
                    "error": f"Requête {keyword} interdite via cet outil. Utilisez les outils dédiés.",
                }

        try:
            if db_type == "postgresql":
                cmd = ["docker", "exec", container, "psql", "-U", user, "-d", db_name, "-c", query]
            elif db_type == "mysql":
                cmd = ["docker", "exec", container, "mysql", "-u", user, db_name, "-e", query]
            else:
                return {"success": False, "error": f"Exécution de requête non supportée pour {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=30,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode().strip()}

            return {"success": True, "result": stdout.decode().strip(), "query": query}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout: requête trop longue (>30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_stats(self, container: str, db_type: str) -> Dict[str, Any]:
        """Statistiques générales de la base de données."""
        try:
            stats = {}

            if db_type == "postgresql":
                queries = {
                    "version": "SELECT version();",
                    "uptime": "SELECT now() - pg_postmaster_start_time() AS uptime;",
                    "connections": "SELECT count(*) FROM pg_stat_activity;",
                    "db_sizes": "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database ORDER BY pg_database_size(datname) DESC LIMIT 5;",
                    "cache_hit_ratio": "SELECT ROUND(100 * sum(blks_hit) / NULLIF(sum(blks_hit + blks_read), 0), 2) AS cache_hit_ratio FROM pg_stat_database;",
                }
                for key, q in queries.items():
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "exec", container, "psql", "-U", "postgres", "-t", "-c", q,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await proc.communicate()
                    if proc.returncode == 0:
                        stats[key] = stdout.decode().strip()

            elif db_type == "mysql":
                cmd = ["docker", "exec", container, "mysql", "-u", "root", "-e",
                       "SHOW GLOBAL STATUS LIKE 'Uptime'; SHOW GLOBAL STATUS LIKE 'Threads_connected'; "
                       "SHOW GLOBAL STATUS LIKE 'Queries';"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                stats["status"] = stdout.decode().strip()

            elif db_type == "redis":
                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", container, "redis-cli", "INFO",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                stats["info"] = stdout.decode().strip()

            return {"success": True, "stats": stats, "db_type": db_type, "container": container}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def dump(
        self,
        db_type: str,
        container_name: str,
        database_name: str,
        db_user: str = "",
        db_password: str = "",
    ) -> Dict[str, Any]:
        """Crée un dump de la base de données dans /backups/databases/."""
        import os
        os.makedirs("/backups/databases", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/backups/databases/{database_name}_{timestamp}.sql"

        try:
            if db_type == "postgresql":
                user = db_user or "postgres"
                cmd = ["docker", "exec", container_name, "pg_dump", "-U", user, database_name]
            elif db_type == "mysql":
                user = db_user or "root"
                pw_arg = f"-p{db_password}" if db_password else ""
                cmd = ["docker", "exec", container_name, "mysqldump", f"-u{user}"] + (
                    [pw_arg] if pw_arg else []
                ) + [database_name]
            elif db_type == "mongodb":
                cmd = ["docker", "exec", container_name, "mongodump", "--db", database_name,
                       "--archive", f"--out=/tmp/{database_name}_{timestamp}.archive"]
            elif db_type == "sqlite":
                cmd = ["docker", "exec", container_name, "sqlite3", f"/data/{database_name}", ".dump"]
            else:
                return {"success": False, "error": f"Type non supporté: {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode().strip()}

            with open(filename, "wb") as f:
                f.write(stdout)

            return {
                "success": True,
                "file": filename,
                "size_bytes": len(stdout),
                "database": database_name,
                "db_type": db_type,
            }

        except Exception as e:
            logger.error(f"dump error: {e}")
            return {"success": False, "error": str(e)}

    async def restore(
        self,
        db_type: str,
        container_name: str,
        database_name: str,
        backup_file: str,
        db_user: str = "",
        db_password: str = "",
    ) -> Dict[str, Any]:
        """Restaure une base de données depuis un fichier de sauvegarde."""
        try:
            if db_type == "postgresql":
                user = db_user or "postgres"
                cmd = f"docker exec -i {container_name} psql -U {user} {database_name} < {backup_file}"
            elif db_type == "mysql":
                user = db_user or "root"
                pw_part = f"-p{db_password}" if db_password else ""
                cmd = f"docker exec -i {container_name} mysql -u{user} {pw_part} {database_name} < {backup_file}"
            else:
                return {"success": False, "error": f"Restauration non supportée pour {db_type}"}

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            success = proc.returncode == 0
            return {
                "success": success,
                "database": database_name,
                "output": (stdout if success else stderr).decode().strip(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def optimize_database(self, container: str, db_type: str, db_name: str) -> Dict[str, Any]:
        """Lance une optimisation (VACUUM/ANALYZE pour PG, OPTIMIZE pour MySQL)."""
        try:
            if db_type == "postgresql":
                cmd = ["docker", "exec", container, "psql", "-U", "postgres", "-d", db_name,
                       "-c", "VACUUM ANALYZE;"]
                action = "VACUUM ANALYZE"
            elif db_type == "mysql":
                cmd = ["docker", "exec", container, "mysqlcheck", "-u", "root",
                       "--optimize", "--all-databases"]
                action = "OPTIMIZE ALL DATABASES"
            else:
                return {"success": False, "error": f"Optimisation non supportée pour {db_type}"}

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            success = proc.returncode == 0
            return {
                "success": success,
                "action": action,
                "output": (stdout if success else stderr).decode().strip(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
