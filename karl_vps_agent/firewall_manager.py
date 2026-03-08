"""
Gestionnaire de pare-feu UFW.
"""
import subprocess
import re
from typing import Dict, Any, List, Optional


class FirewallManager:

    def _run(self, cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def get_status(self) -> Dict[str, Any]:
        result = self._run(["ufw", "status", "verbose"])
        active = "active" in result.stdout.lower()
        return {"active": active, "output": result.stdout, "error": result.stderr}

    def list_rules(self) -> Dict[str, Any]:
        result = self._run(["ufw", "status", "numbered"])
        rules = []
        for line in result.stdout.splitlines():
            m = re.match(r"\[\s*(\d+)\]\s+(.+)", line)
            if m:
                rules.append({"num": int(m.group(1)), "rule": m.group(2).strip()})
        return {"rules": rules, "count": len(rules)}

    def add_rule(
        self,
        action: str,                   # allow | deny | limit
        port: Optional[int] = None,
        proto: str = "tcp",
        from_ip: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        if action not in ("allow", "deny", "limit"):
            return {"success": False, "error": "action must be allow|deny|limit"}

        cmd = ["ufw"]
        if from_ip:
            cmd += ["from", from_ip]
            if port:
                cmd += ["to", "any", "port", str(port), "proto", proto]
            else:
                cmd += ["to", "any"]
            cmd = ["ufw"] + [action] + cmd[1:]
        else:
            if port:
                cmd += [action, f"{port}/{proto}"]
            else:
                return {"success": False, "error": "port or from_ip required"}

        result = self._run(cmd)
        if comment:
            # UFW ne supporte les commentaires que depuis Ubuntu 16.04+
            pass
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
        }

    def remove_rule(
        self,
        port: Optional[int] = None,
        from_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        if from_ip:
            result = self._run(["ufw", "delete", "deny", "from", from_ip])
            if result.returncode != 0:
                result = self._run(["ufw", "delete", "allow", "from", from_ip])
        elif port:
            result = self._run(["ufw", "--force", "delete", "allow", str(port)])
            if result.returncode != 0:
                result = self._run(["ufw", "--force", "delete", "deny", str(port)])
        else:
            return {"success": False, "error": "port or from_ip required"}

        return {"success": result.returncode == 0, "output": result.stdout.strip()}

    def block_ip(self, ip: str, comment: Optional[str] = None) -> Dict[str, Any]:
        """Bloque complètement une IP (toutes connexions entrantes + sortantes)."""
        result_in = self._run(["ufw", "deny", "from", ip, "to", "any"])
        return {
            "success": result_in.returncode == 0,
            "ip": ip,
            "output": result_in.stdout.strip(),
        }

    def detect_brute_force(self, threshold: int = 10) -> Dict[str, Any]:
        """Analyse les logs auth pour détecter les tentatives de brute force SSH."""
        suspicious = {}
        try:
            result = self._run(
                ["grep", "Failed password", "/var/log/auth.log"],
                timeout=5
            )
            for line in result.stdout.splitlines():
                m = re.search(r"from (\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    ip = m.group(1)
                    suspicious[ip] = suspicious.get(ip, 0) + 1
        except Exception:
            # Essayer journalctl si auth.log indisponible
            try:
                result = self._run(
                    ["journalctl", "-u", "sshd", "--no-pager", "-n", "1000"],
                    timeout=5
                )
                for line in result.stdout.splitlines():
                    if "Failed" in line or "Invalid" in line:
                        m = re.search(r"from (\d+\.\d+\.\d+\.\d+)", line)
                        if m:
                            ip = m.group(1)
                            suspicious[ip] = suspicious.get(ip, 0) + 1
            except Exception:
                pass

        attackers = [
            {"ip": ip, "attempts": count}
            for ip, count in sorted(suspicious.items(), key=lambda x: -x[1])
            if count >= threshold
        ]
        return {
            "suspicious_ips": attackers,
            "threshold": threshold,
            "total_suspicious": len(attackers),
        }
