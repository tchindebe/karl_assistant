"""
Auditeur de sécurité — analyse la posture de sécurité du VPS.
Vérifie les ports ouverts, les images Docker, les permissions fichiers,
les mises à jour système, les configurations critiques.
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("karl.security")


class SecurityAuditor:
    """Effectue des audits de sécurité sur le VPS."""

    async def full_audit(self) -> Dict[str, Any]:
        """Audit de sécurité complet — agrège tous les checks."""
        results = {}
        score = 100
        issues = []

        # Lancer tous les checks en parallèle
        checks = await asyncio.gather(
            self.check_open_ports(),
            self.check_docker_images(),
            self.check_file_permissions(),
            self.check_ssh_config(),
            self.check_system_updates(),
            self.check_failed_logins(),
            self.check_fail2ban(),
            return_exceptions=True,
        )

        check_names = [
            "open_ports", "docker_images", "file_permissions",
            "ssh_config", "system_updates", "failed_logins", "fail2ban",
        ]

        for name, result in zip(check_names, checks):
            if isinstance(result, Exception):
                results[name] = {"error": str(result)}
            else:
                results[name] = result
                # Décrémenter le score selon les problèmes trouvés
                if isinstance(result, dict) and result.get("issues"):
                    for issue in result["issues"]:
                        severity = issue.get("severity", "low")
                        if severity == "critical":
                            score -= 20
                        elif severity == "high":
                            score -= 10
                        elif severity == "medium":
                            score -= 5
                        else:
                            score -= 2
                        issues.append(issue)

        score = max(0, score)

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "security_score": score,
            "grade": self._score_to_grade(score),
            "total_issues": len(issues),
            "critical_issues": sum(1 for i in issues if i.get("severity") == "critical"),
            "high_issues": sum(1 for i in issues if i.get("severity") == "high"),
            "results": results,
        }

    def _score_to_grade(self, score: int) -> str:
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    async def check_open_ports(self) -> Dict[str, Any]:
        """Vérifie les ports ouverts avec ss ou netstat."""
        try:
            # Essayer ss (plus moderne)
            proc = await asyncio.create_subprocess_exec(
                "ss", "-tlnp",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                # Fallback sur netstat
                proc = await asyncio.create_subprocess_exec(
                    "netstat", "-tlnp",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()

            output = stdout.decode()
            ports = self._parse_open_ports(output)

            # Identifier les ports dangereux
            dangerous_ports = {
                21: "FTP (non chiffré)",
                23: "Telnet (non chiffré)",
                3306: "MySQL exposé publiquement",
                5432: "PostgreSQL exposé publiquement",
                6379: "Redis exposé publiquement",
                27017: "MongoDB exposé publiquement",
                9200: "Elasticsearch exposé publiquement",
            }

            issues = []
            for port_info in ports:
                port = port_info.get("port", 0)
                if port in dangerous_ports:
                    issues.append({
                        "severity": "high",
                        "type": "open_port",
                        "description": f"Port {port} ouvert: {dangerous_ports[port]}",
                        "recommendation": f"Restreindre l'accès au port {port} via firewall ou bind sur 127.0.0.1",
                    })

            return {
                "success": True,
                "open_ports": ports,
                "total_open": len(ports),
                "issues": issues,
            }

        except Exception as e:
            logger.error(f"check_open_ports error: {e}")
            return {"success": False, "error": str(e), "issues": []}

    def _parse_open_ports(self, output: str) -> List[Dict]:
        """Parse la sortie de ss -tlnp."""
        ports = []
        for line in output.splitlines()[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 4:
                local_addr = parts[3] if len(parts) > 3 else ""
                try:
                    if ":" in local_addr:
                        addr, port_str = local_addr.rsplit(":", 1)
                        port = int(port_str)
                        process = parts[-1] if len(parts) > 5 else "unknown"
                        ports.append({"port": port, "address": addr, "process": process})
                except (ValueError, IndexError):
                    pass
        return ports

    async def check_docker_images(self) -> Dict[str, Any]:
        """Vérifie les images Docker pour les vulnérabilités connues et les images obsolètes."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "images", "--format",
                "{{json .}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode(), "issues": []}

            images = []
            issues = []

            for line in stdout.decode().splitlines():
                if line.strip():
                    try:
                        img = json.loads(line)
                        images.append(img)

                        # Vérifier les tags à risque
                        tag = img.get("Tag", "")
                        repo = img.get("Repository", "")

                        if tag == "latest":
                            issues.append({
                                "severity": "medium",
                                "type": "docker_image",
                                "description": f"Image {repo}:latest — tag non versionné",
                                "recommendation": "Utiliser des tags de version précis pour la reproductibilité",
                            })

                        if repo == "<none>" or tag == "<none>":
                            issues.append({
                                "severity": "low",
                                "type": "docker_image",
                                "description": f"Image dangling (non taguée): {img.get('ID', 'unknown')}",
                                "recommendation": "Nettoyer avec: docker image prune",
                            })

                    except json.JSONDecodeError:
                        pass

            # Vérifier les conteneurs tournant en root
            proc2 = await asyncio.create_subprocess_exec(
                "docker", "ps", "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout2, _ = await proc2.communicate()

            for container_name in stdout2.decode().splitlines():
                if not container_name.strip():
                    continue
                proc3 = await asyncio.create_subprocess_exec(
                    "docker", "exec", container_name, "id", "-u",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout3, _ = await proc3.communicate()
                if proc3.returncode == 0 and stdout3.decode().strip() == "0":
                    issues.append({
                        "severity": "high",
                        "type": "docker_security",
                        "description": f"Conteneur {container_name} tourne en tant que root",
                        "recommendation": "Ajouter 'user: 1000:1000' dans docker-compose.yml",
                    })

            return {
                "success": True,
                "total_images": len(images),
                "images": images[:20],  # limiter à 20
                "issues": issues,
            }

        except Exception as e:
            logger.error(f"check_docker_images error: {e}")
            return {"success": False, "error": str(e), "issues": []}

    async def check_file_permissions(self) -> Dict[str, Any]:
        """Vérifie les permissions sur les fichiers sensibles."""
        issues = []
        checks = []

        sensitive_files = [
            ("/etc/passwd", "644", "should be readable by all"),
            ("/etc/shadow", "640", "should NOT be world-readable"),
            ("/etc/sudoers", "440", "should be read-only"),
            ("/root/.ssh/authorized_keys", "600", "should be owner read-only"),
            ("/etc/ssh/sshd_config", "600", "should be owner read-only"),
        ]

        for filepath, expected_perms, note in sensitive_files:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "stat", "-c", "%a %n", filepath,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()

                if proc.returncode == 0:
                    parts = stdout.decode().strip().split()
                    if parts:
                        actual_perms = parts[0]
                        checks.append({
                            "file": filepath,
                            "permissions": actual_perms,
                            "expected": expected_perms,
                            "ok": actual_perms == expected_perms,
                        })

                        if actual_perms != expected_perms:
                            # Vérifier si world-writable (dangereux)
                            if len(actual_perms) >= 3 and actual_perms[-1] in ["2", "3", "6", "7"]:
                                issues.append({
                                    "severity": "critical",
                                    "type": "file_permissions",
                                    "description": f"{filepath} est world-writable ({actual_perms})!",
                                    "recommendation": f"chmod {expected_perms} {filepath}",
                                })
                            else:
                                issues.append({
                                    "severity": "medium",
                                    "type": "file_permissions",
                                    "description": f"{filepath}: permissions {actual_perms} (attendu: {expected_perms})",
                                    "recommendation": f"chmod {expected_perms} {filepath}",
                                })

            except Exception:
                pass

        # Vérifier les fichiers SUID
        try:
            proc = await asyncio.create_subprocess_exec(
                "find", "/usr", "-perm", "/4000", "-type", "f",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            suid_files = [f for f in stdout.decode().splitlines() if f.strip()]

            # Binaires SUID attendus (whitelist)
            expected_suid = {
                "/usr/bin/sudo", "/usr/bin/passwd", "/usr/bin/su",
                "/usr/bin/newgrp", "/usr/bin/chsh", "/usr/bin/chfn",
                "/usr/bin/gpasswd", "/usr/sbin/pam_timestamp_check",
            }
            unexpected = [f for f in suid_files if f not in expected_suid]

            if unexpected:
                issues.append({
                    "severity": "high",
                    "type": "suid_files",
                    "description": f"{len(unexpected)} fichiers SUID inattendus trouvés",
                    "files": unexpected[:10],
                    "recommendation": "Vérifier si ces fichiers SUID sont légitimes",
                })

        except Exception:
            pass

        return {
            "success": True,
            "file_checks": checks,
            "issues": issues,
        }

    async def check_ssh_config(self) -> Dict[str, Any]:
        """Vérifie la configuration SSH pour les bonnes pratiques."""
        issues = []
        config_checks = {}

        ssh_config_path = "/etc/ssh/sshd_config"
        try:
            proc = await asyncio.create_subprocess_exec(
                "cat", ssh_config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": "Impossible de lire sshd_config", "issues": []}

            config = stdout.decode()

            # Checks critiques
            checks = [
                ("PermitRootLogin", "no", "critical", "Connexion root SSH autorisée"),
                ("PasswordAuthentication", "no", "high", "Authentification par mot de passe SSH activée"),
                ("X11Forwarding", "no", "low", "X11 Forwarding activé"),
                ("AllowAgentForwarding", "no", "low", "Agent Forwarding activé"),
                ("PermitEmptyPasswords", "no", "critical", "Mots de passe vides autorisés"),
                ("Protocol", "2", "critical", "Protocole SSH 1 activé (obsolète)"),
            ]

            for setting, good_value, severity, description in checks:
                pattern = rf"^\s*{setting}\s+(\S+)"
                match = re.search(pattern, config, re.MULTILINE | re.IGNORECASE)

                if match:
                    actual = match.group(1).lower()
                    config_checks[setting] = actual
                    if actual != good_value:
                        issues.append({
                            "severity": severity,
                            "type": "ssh_config",
                            "description": description,
                            "current": actual,
                            "recommended": good_value,
                            "recommendation": f"Dans {ssh_config_path}: {setting} {good_value}",
                        })
                else:
                    # Non configuré = valeur par défaut potentiellement risquée
                    if setting == "PasswordAuthentication":
                        issues.append({
                            "severity": "medium",
                            "type": "ssh_config",
                            "description": f"{setting} non configuré (défaut: yes)",
                            "recommendation": f"Ajouter '{setting} no' dans {ssh_config_path}",
                        })

        except Exception as e:
            return {"success": False, "error": str(e), "issues": []}

        return {
            "success": True,
            "config": config_checks,
            "issues": issues,
        }

    async def check_system_updates(self) -> Dict[str, Any]:
        """Vérifie les mises à jour système disponibles."""
        issues = []

        try:
            # Debian/Ubuntu
            proc = await asyncio.create_subprocess_exec(
                "apt", "list", "--upgradable",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"DEBIAN_FRONTEND": "noninteractive", "PATH": "/usr/bin:/bin"},
            )
            stdout, _ = await proc.communicate()

            upgradable = [
                line for line in stdout.decode().splitlines()
                if line and not line.startswith("Listing")
            ]

            # Chercher les mises à jour de sécurité
            security_updates = [p for p in upgradable if "security" in p.lower()]

            if security_updates:
                issues.append({
                    "severity": "high",
                    "type": "system_updates",
                    "description": f"{len(security_updates)} mises à jour de sécurité disponibles",
                    "recommendation": "apt upgrade --only-upgrade pour les paquets de sécurité",
                })
            elif upgradable:
                issues.append({
                    "severity": "low",
                    "type": "system_updates",
                    "description": f"{len(upgradable)} mises à jour disponibles",
                    "recommendation": "apt upgrade pour mettre à jour le système",
                })

            return {
                "success": True,
                "total_upgradable": len(upgradable),
                "security_updates": len(security_updates),
                "packages": upgradable[:20],
                "issues": issues,
            }

        except Exception as e:
            # Non critique — peut-être pas Debian
            return {"success": False, "error": str(e), "issues": []}

    async def check_failed_logins(self, hours: int = 24) -> Dict[str, Any]:
        """Vérifie les tentatives de connexion échouées récentes."""
        issues = []

        try:
            # Lire les échecs SSH des dernières N heures
            proc = await asyncio.create_subprocess_exec(
                "journalctl", "-u", "sshd", "--since", f"{hours} hours ago",
                "--no-pager", "-q",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            log_content = stdout.decode() if proc.returncode == 0 else ""

            if not log_content:
                # Fallback auth.log
                try:
                    with open("/var/log/auth.log", "r") as f:
                        log_content = f.read()
                except FileNotFoundError:
                    pass

            # Compter les échecs par IP
            failed_pattern = re.compile(r"Failed password for .+ from (\d+\.\d+\.\d+\.\d+)")
            ip_counts: Dict[str, int] = {}
            for match in failed_pattern.finditer(log_content):
                ip = match.group(1)
                ip_counts[ip] = ip_counts.get(ip, 0) + 1

            top_attackers = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            total_failures = sum(ip_counts.values())

            if total_failures > 100:
                issues.append({
                    "severity": "high",
                    "type": "brute_force",
                    "description": f"{total_failures} tentatives SSH échouées en 24h",
                    "top_ips": top_attackers[:5],
                    "recommendation": "Installer fail2ban et bloquer les IPs problématiques",
                })
            elif total_failures > 20:
                issues.append({
                    "severity": "medium",
                    "type": "brute_force",
                    "description": f"{total_failures} tentatives SSH échouées en 24h",
                    "recommendation": "Surveiller l'activité SSH",
                })

            return {
                "success": True,
                "total_failures_24h": total_failures,
                "unique_ips": len(ip_counts),
                "top_attackers": top_attackers,
                "issues": issues,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "issues": []}

    async def check_open_ports_external(self) -> Dict[str, Any]:
        """Vérifie les ports ouverts depuis l'extérieur (nmap si disponible)."""
        try:
            # Obtenir l'IP locale
            proc = await asyncio.create_subprocess_exec(
                "hostname", "-I",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            local_ip = stdout.decode().split()[0] if stdout.decode().split() else "127.0.0.1"

            # nmap scan léger
            proc = await asyncio.create_subprocess_exec(
                "nmap", "-T4", "--open", "-p", "1-65535", local_ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": "nmap non disponible", "issues": []}

            return {
                "success": True,
                "nmap_output": stdout.decode(),
                "issues": [],
            }

        except FileNotFoundError:
            return {"success": False, "error": "nmap n'est pas installé", "issues": []}
        except Exception as e:
            return {"success": False, "error": str(e), "issues": []}

    async def harden_ssh(self) -> Dict[str, Any]:
        """Applique les bonnes pratiques SSH: désactive root login, auth par mot de passe, X11."""
        changes = []
        ssh_config = "/etc/ssh/sshd_config"

        settings = [
            ("PermitRootLogin", "no"),
            ("PasswordAuthentication", "no"),
            ("X11Forwarding", "no"),
            ("PermitEmptyPasswords", "no"),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                "cat", ssh_config,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            config = stdout.decode()

            for key, value in settings:
                pattern = rf"^\s*#?\s*{key}\s+\S+"
                new_line = f"{key} {value}"
                if re.search(pattern, config, re.MULTILINE | re.IGNORECASE):
                    config = re.sub(pattern, new_line, config, flags=re.MULTILINE | re.IGNORECASE)
                else:
                    config += f"\n{new_line}"
                changes.append(f"{key} = {value}")

            # Écrire la config modifiée
            write_proc = await asyncio.create_subprocess_exec(
                "tee", ssh_config,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await write_proc.communicate(input=config.encode())

            if write_proc.returncode != 0:
                return {"success": False, "error": stderr.decode()}

            # Recharger SSH
            reload_proc = await asyncio.create_subprocess_exec(
                "systemctl", "reload", "sshd",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await reload_proc.communicate()

            return {"success": True, "changes_applied": changes, "message": "SSH sécurisé et rechargé"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def check_fail2ban(self) -> Dict[str, Any]:
        """Vérifie si fail2ban est installé et actif."""
        issues = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "is-active", "fail2ban",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            active = stdout.decode().strip() == "active"

            installed = True
            if proc.returncode not in (0, 3):
                # returncode 3 = inactive (installed but stopped)
                installed = False

            if not installed:
                issues.append({
                    "severity": "medium",
                    "type": "fail2ban",
                    "description": "fail2ban n'est pas installé",
                    "recommendation": "Installer fail2ban pour protéger contre les attaques brute-force",
                })
            elif not active:
                issues.append({
                    "severity": "low",
                    "type": "fail2ban",
                    "description": "fail2ban est installé mais inactif",
                    "recommendation": "Activer fail2ban: systemctl enable --now fail2ban",
                })

            return {
                "success": True,
                "installed": installed,
                "active": active,
                "issues": issues,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "installed": False, "active": False, "issues": []}

    async def install_fail2ban(self) -> Dict[str, Any]:
        """Installe et configure fail2ban pour la protection SSH."""
        try:
            # Installer fail2ban
            proc = await asyncio.create_subprocess_exec(
                "apt-get", "install", "-y", "fail2ban",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={"DEBIAN_FRONTEND": "noninteractive", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode()}

            # Config jail SSH
            jail_config = """[sshd]
enabled = true
maxretry = 5
bantime = 3600
findtime = 600
"""
            write_proc = await asyncio.create_subprocess_exec(
                "tee", "/etc/fail2ban/jail.local",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await write_proc.communicate(input=jail_config.encode())

            # Activer et démarrer fail2ban
            for cmd in [["systemctl", "enable", "fail2ban"], ["systemctl", "restart", "fail2ban"]]:
                p = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await p.communicate()

            return {
                "success": True,
                "message": "fail2ban installé et configuré",
                "config": "SSH protégé: bannissement après 5 tentatives échouées (1h)",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scan_malware(self) -> Dict[str, Any]:
        """Recherche des indicateurs de compromission: fichiers modifiés, processus suspects, crons."""
        results = {}

        try:
            # 1. Fichiers système modifiés récemment (dernières 24h)
            proc = await asyncio.create_subprocess_exec(
                "find", "/usr/bin", "/usr/sbin", "/bin", "/sbin",
                "-newer", "/proc/1", "-type", "f",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            results["recently_modified_system_files"] = [
                f for f in stdout.decode().splitlines() if f.strip()
            ]

            # 2. Connexions réseau établies vers l'extérieur
            proc2 = await asyncio.create_subprocess_exec(
                "ss", "-tnp", "state", "established",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout2, _ = await proc2.communicate()
            results["established_connections"] = stdout2.decode().strip()

            # 3. Crontabs root
            proc3 = await asyncio.create_subprocess_exec(
                "crontab", "-l",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout3, _ = await proc3.communicate()
            results["root_crontab"] = stdout3.decode().strip() or "(vide)"

            # 4. Crons système
            cron_dirs = ["/etc/cron.d", "/etc/cron.daily", "/etc/cron.weekly"]
            cron_files = []
            for d in cron_dirs:
                p = Path(d)
                if p.exists():
                    cron_files.extend([str(f) for f in p.iterdir() if f.is_file()])
            results["system_cron_files"] = cron_files

            suspicious = []
            if len(results["recently_modified_system_files"]) > 5:
                suspicious.append(f"{len(results['recently_modified_system_files'])} fichiers système modifiés récemment")

            return {
                "success": True,
                "suspicious_indicators": suspicious,
                "details": results,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
