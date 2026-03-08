"""
Webhooks CI/CD — reçoit les push events GitHub/GitLab et déclenche un déploiement.
Sécurisé par HMAC-SHA256 (GitHub) ou secret token (GitLab).
"""
import hashlib
import hmac
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from core.config import get_settings
from services.notification_service import send_notification
from tools.vps_tools import _agent_client

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger("karl.webhooks")
settings = get_settings()


# ── Vérification de signature ──────────────────────────────────────────────────

def _verify_github_signature(payload: bytes, signature: str) -> bool:
    """Vérifie la signature HMAC-SHA256 de GitHub."""
    if not settings.github_webhook_secret:
        logger.warning("GITHUB_WEBHOOK_SECRET non configuré — webhook non sécurisé")
        return True  # Permissif si pas de secret configuré

    if not signature or not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def _verify_gitlab_token(token: Optional[str]) -> bool:
    """Vérifie le secret token GitLab."""
    if not settings.gitlab_webhook_secret:
        return True  # Permissif si pas de secret configuré
    return token == settings.gitlab_webhook_secret


# ── Logique de déploiement ─────────────────────────────────────────────────────

async def _deploy_from_git(
    repo_url: str,
    branch: str,
    app_name: str,
    commit_sha: str,
    commit_message: str,
    pusher: str,
    environment: str = "production",
) -> None:
    """Lance le déploiement depuis le VPS Agent en arrière-plan."""
    logger.info(f"CI/CD deploy: {app_name} from {repo_url}@{branch} [{commit_sha[:8]}]")

    try:
        async with _agent_client() as client:
            resp = await client.post("/deploy/git", json={
                "repo_url": repo_url,
                "branch": branch,
                "app_name": app_name,
                "environment": environment,
            })

        success = resp.status_code == 200
        result = resp.json() if success else {}

        message = (
            f"**{app_name}** déployé depuis `{branch}`\n\n"
            f"**Commit**: `{commit_sha[:8]}` — {commit_message[:100]}\n"
            f"**Auteur**: {pusher}\n"
            f"**Environnement**: {environment}\n"
        )

        if success:
            message += f"\n✅ Déploiement réussi"
            if result.get("container_id"):
                message += f"\n**Container**: `{result['container_id'][:12]}`"
        else:
            message += f"\n❌ Déploiement échoué: {resp.text[:200]}"

        await send_notification(
            message,
            title=f"CI/CD — {app_name}",
            level="info" if success else "critical",
        )

    except Exception as e:
        logger.error(f"_deploy_from_git error: {e}")
        await send_notification(
            f"Erreur lors du déploiement CI/CD de **{app_name}**: {e}",
            title=f"CI/CD Erreur — {app_name}",
            level="critical",
        )


# ── Routes webhook ─────────────────────────────────────────────────────────────

@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """
    Reçoit les webhooks GitHub.
    Configure sur GitHub: Settings → Webhooks → Add webhook
    Événements: push, pull_request (merged)
    """
    payload = await request.body()

    # Vérifier la signature
    if not _verify_github_signature(payload, x_hub_signature_256 or ""):
        logger.warning("GitHub webhook: signature invalide")
        raise HTTPException(status_code=401, detail="Signature invalide")

    # Parser le payload
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload JSON invalide")

    event = x_github_event or "unknown"
    logger.info(f"GitHub webhook reçu: {event}")

    # Traiter uniquement les push sur les branches configurées
    if event == "push":
        ref = data.get("ref", "")  # ex: "refs/heads/main"
        branch = ref.replace("refs/heads/", "")
        allowed_branches = settings.ci_deploy_branches  # défaut: ["main", "production"]

        if branch not in allowed_branches:
            return {"status": "ignored", "reason": f"Branch '{branch}' not in deploy branches"}

        repo = data.get("repository", {})
        repo_url = repo.get("clone_url") or repo.get("ssh_url", "")
        repo_name = repo.get("name", "unknown")

        # Utiliser le nom du repo comme nom d'app (sanitisé)
        app_name = repo_name.lower().replace("_", "-").replace(" ", "-")

        # Info du commit
        head_commit = data.get("head_commit") or {}
        commit_sha = head_commit.get("id", data.get("after", "unknown"))
        commit_message = head_commit.get("message", "No message")
        pusher = data.get("pusher", {}).get("name", "unknown")

        # Déploiement en arrière-plan
        background_tasks.add_task(
            _deploy_from_git,
            repo_url=repo_url,
            branch=branch,
            app_name=app_name,
            commit_sha=commit_sha,
            commit_message=commit_message,
            pusher=pusher,
            environment="production" if branch == "main" else branch,
        )

        return {
            "status": "accepted",
            "app": app_name,
            "branch": branch,
            "commit": commit_sha[:8],
        }

    # Pull request mergé
    elif event == "pull_request":
        pr = data.get("pull_request", {})
        action = data.get("action")

        if action == "closed" and pr.get("merged"):
            branch = pr.get("base", {}).get("ref", "main")
            repo_url = data.get("repository", {}).get("clone_url", "")
            app_name = data.get("repository", {}).get("name", "unknown")
            app_name = app_name.lower().replace("_", "-")

            background_tasks.add_task(
                _deploy_from_git,
                repo_url=repo_url,
                branch=branch,
                app_name=app_name,
                commit_sha=pr.get("merge_commit_sha", "unknown"),
                commit_message=f"PR #{pr.get('number')}: {pr.get('title', '')}",
                pusher=pr.get("user", {}).get("login", "unknown"),
            )

            return {"status": "accepted", "event": "pr_merged", "app": app_name}

    return {"status": "ignored", "event": event}


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitlab_token: Optional[str] = Header(None),
    x_gitlab_event: Optional[str] = Header(None),
):
    """
    Reçoit les webhooks GitLab.
    Configure sur GitLab: Settings → Webhooks → Add webhook
    Événements: Push events, Merge Request Events
    """
    # Vérifier le secret token
    if not _verify_gitlab_token(x_gitlab_token):
        raise HTTPException(status_code=401, detail="Token invalide")

    payload = await request.body()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload JSON invalide")

    event = x_gitlab_event or data.get("object_kind", "unknown")
    logger.info(f"GitLab webhook reçu: {event}")

    if event in ("Push Hook", "push"):
        ref = data.get("ref", "")
        branch = ref.replace("refs/heads/", "")
        allowed_branches = settings.ci_deploy_branches

        if branch not in allowed_branches:
            return {"status": "ignored", "reason": f"Branch '{branch}' not in deploy branches"}

        project = data.get("project", {})
        repo_url = project.get("http_url") or project.get("git_http_url", "")
        app_name = project.get("name", "unknown").lower().replace("_", "-")

        commits = data.get("commits", [{}])
        last_commit = commits[0] if commits else {}
        commit_sha = last_commit.get("id", data.get("checkout_sha", "unknown"))
        commit_message = last_commit.get("message", "No message")
        pusher = data.get("user_username", data.get("user_name", "unknown"))

        background_tasks.add_task(
            _deploy_from_git,
            repo_url=repo_url,
            branch=branch,
            app_name=app_name,
            commit_sha=commit_sha,
            commit_message=commit_message,
            pusher=pusher,
        )

        return {"status": "accepted", "app": app_name, "branch": branch}

    elif event in ("Merge Request Hook", "merge_request"):
        attrs = data.get("object_attributes", {})
        if attrs.get("state") == "merged":
            project = data.get("project", {})
            repo_url = project.get("http_url", "")
            app_name = project.get("name", "unknown").lower().replace("_", "-")
            branch = attrs.get("target_branch", "main")

            background_tasks.add_task(
                _deploy_from_git,
                repo_url=repo_url,
                branch=branch,
                app_name=app_name,
                commit_sha=attrs.get("merge_commit_sha", "unknown"),
                commit_message=f"MR !{attrs.get('iid')}: {attrs.get('title', '')}",
                pusher=data.get("user", {}).get("username", "unknown"),
            )

            return {"status": "accepted", "event": "mr_merged", "app": app_name}

    return {"status": "ignored", "event": event}


@router.get("/status")
async def webhook_status():
    """Retourne l'état de configuration des webhooks."""
    return {
        "github": {
            "endpoint": "/webhooks/github",
            "secret_configured": bool(settings.github_webhook_secret),
            "deploy_branches": settings.ci_deploy_branches,
        },
        "gitlab": {
            "endpoint": "/webhooks/gitlab",
            "secret_configured": bool(settings.gitlab_webhook_secret),
            "deploy_branches": settings.ci_deploy_branches,
        },
    }
