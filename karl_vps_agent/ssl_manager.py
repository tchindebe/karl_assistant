"""
Gestion SSL via Certbot — certificats Let's Encrypt, suivi d'expiration, alertes.
"""
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


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


class SSLManager:

    async def enable(self, domain: str, email: str) -> Dict[str, Any]:
        """Obtient un certificat SSL via certbot --nginx."""
        cmd = (
            f"certbot --nginx -d {domain} --email {email} "
            f"--agree-tos --non-interactive --redirect"
        )
        result = await _run(cmd)
        return {
            "success": result["returncode"] == 0,
            "domain": domain,
            "output": result["stdout"],
            "error": result["stderr"] if result["returncode"] != 0 else None,
        }

    async def renew_all(self) -> Dict[str, Any]:
        """Renouvelle tous les certificats."""
        result = await _run("certbot renew --non-interactive")
        return {
            "success": result["returncode"] == 0,
            "output": result["stdout"],
            "error": result["stderr"] if result["returncode"] != 0 else None,
        }

    async def list_certs(self) -> Dict[str, Any]:
        """Liste les certificats installés."""
        result = await _run("certbot certificates")
        certs = []
        current = {}
        for line in result["stdout"].splitlines():
            line = line.strip()
            if line.startswith("Certificate Name:"):
                if current:
                    certs.append(current)
                current = {"name": line.split(":", 1)[1].strip()}
            elif line.startswith("Domains:") and current:
                current["domains"] = line.split(":", 1)[1].strip()
            elif line.startswith("Expiry Date:") and current:
                current["expiry"] = line.split(":", 1)[1].strip()
            elif line.startswith("Certificate Path:") and current:
                current["path"] = line.split(":", 1)[1].strip()

        if current:
            certs.append(current)

        return {"certificates": certs, "raw": result["stdout"]}

    async def get_expiry_info(self) -> Dict[str, Any]:
        """Retourne les infos d'expiration pour tous les certificats avec alertes."""
        certs_result = await self.list_certs()
        certs = certs_result.get("certificates", [])

        now = datetime.now()
        enriched = []
        alerts = []

        for cert in certs:
            expiry_raw = cert.get("expiry", "")
            days_left = None

            # Parser la date d'expiration: "2025-06-15 12:00:00+00:00 (VALID: 89 days)"
            match = re.search(r"VALID:\s*(\d+)\s*days", expiry_raw)
            if match:
                days_left = int(match.group(1))

            # Tenter de parser la date directement
            if days_left is None:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", expiry_raw)
                if date_match:
                    try:
                        expiry_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                        days_left = (expiry_date - now).days
                    except ValueError:
                        pass

            status = "ok"
            if days_left is not None:
                if days_left < 0:
                    status = "expired"
                    alerts.append({
                        "severity": "critical",
                        "domain": cert.get("name"),
                        "message": f"Certificat EXPIRÉ depuis {abs(days_left)} jours!",
                    })
                elif days_left < 7:
                    status = "critical"
                    alerts.append({
                        "severity": "critical",
                        "domain": cert.get("name"),
                        "message": f"Certificat expire dans {days_left} jours — RENOUVELER IMMÉDIATEMENT",
                    })
                elif days_left < 30:
                    status = "warning"
                    alerts.append({
                        "severity": "warning",
                        "domain": cert.get("name"),
                        "message": f"Certificat expire dans {days_left} jours",
                    })

            enriched.append({
                **cert,
                "days_left": days_left,
                "status": status,
            })

        return {
            "success": True,
            "certificates": enriched,
            "alerts": alerts,
            "total": len(enriched),
            "expired": sum(1 for c in enriched if c["status"] == "expired"),
            "critical": sum(1 for c in enriched if c["status"] == "critical"),
            "warning": sum(1 for c in enriched if c["status"] == "warning"),
        }

    async def check_domain_ssl(self, domain: str, port: int = 443) -> Dict[str, Any]:
        """Vérifie le certificat SSL d'un domaine depuis l'extérieur (via openssl)."""
        cmd = (
            f"echo | openssl s_client -servername {domain} -connect {domain}:{port} 2>/dev/null "
            f"| openssl x509 -noout -dates -subject -issuer 2>/dev/null"
        )
        result = await _run(cmd)

        if result["returncode"] != 0 or not result["stdout"]:
            return {
                "success": False,
                "domain": domain,
                "error": "Impossible de récupérer le certificat SSL",
            }

        output = result["stdout"]
        info: Dict[str, Any] = {"domain": domain, "success": True}

        for line in output.splitlines():
            if "notBefore=" in line:
                info["not_before"] = line.split("=", 1)[1].strip()
            elif "notAfter=" in line:
                not_after = line.split("=", 1)[1].strip()
                info["not_after"] = not_after
                # Calculer jours restants
                try:
                    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    info["days_left"] = (expiry - datetime.now()).days
                except ValueError:
                    pass
            elif "subject=" in line:
                info["subject"] = line.split("=", 1)[1].strip()
            elif "issuer=" in line:
                info["issuer"] = line.split("=", 1)[1].strip()

        days_left = info.get("days_left", 0)
        info["status"] = (
            "expired" if days_left < 0
            else "critical" if days_left < 7
            else "warning" if days_left < 30
            else "ok"
        )

        return info

    async def force_renew(self, domain: str) -> Dict[str, Any]:
        """Force le renouvellement d'un certificat spécifique (ignore la date d'expiration)."""
        result = await _run(f"certbot renew --cert-name {domain} --force-renewal --non-interactive")
        return {
            "success": result["returncode"] == 0,
            "domain": domain,
            "output": result["stdout"],
            "error": result["stderr"] if result["returncode"] != 0 else None,
        }

    async def revoke(self, domain: str) -> Dict[str, Any]:
        """Révoque et supprime un certificat SSL."""
        result = await _run(f"certbot delete --cert-name {domain} --non-interactive")
        return {
            "success": result["returncode"] == 0,
            "domain": domain,
            "output": result["stdout"],
        }
