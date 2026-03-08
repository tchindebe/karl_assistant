"""
Karl Brain — Application FastAPI principale.
Point d'entrée du serveur IA.
"""
import sys
from pathlib import Path

# Ajouter le dossier karl_brain au path
sys.path.insert(0, str(Path(__file__).parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from core.config import get_settings
from core.database import init_db
from api.auth import router as auth_router
from api.chat import router as chat_router
from api.metrics import router as metrics_router
from api.deployments import router as deployments_router
from api.dashboard import router as dashboard_router

settings = get_settings()


def _validate_settings() -> None:
    """Fail fast if required env vars are missing."""
    errors = []
    if not settings.vps_agent_api_key:
        errors.append("VPS_AGENT_API_KEY is not set")
    if not settings.karl_admin_password:
        errors.append("KARL_ADMIN_PASSWORD is not set")
    if not settings.jwt_secret:
        errors.append("JWT_SECRET is not set")
    if settings.provider == "anthropic" and not settings.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is not set (required when PROVIDER=anthropic)")
    if settings.provider == "openai" and not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is not set (required when PROVIDER=openai)")
    if settings.provider == "gemini" and not settings.gemini_api_key:
        errors.append("GEMINI_API_KEY is not set (required when PROVIDER=gemini)")
    if errors:
        for e in errors:
            print(f"[FATAL] {e}", flush=True)
        raise SystemExit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_settings()
    # Initialiser la DB au démarrage
    await init_db()
    print(f"Karl Brain démarré — Modèle: {settings.claude_model}")
    print(f"VPS Agent: {settings.vps_agent_url}")
    yield
    print("Karl Brain arrêté.")


app = FastAPI(
    title="Karl — AI VPS Assistant",
    description="Assistant IA pour la gestion de VPS, déploiement, monitoring et CRM",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permettre les requêtes du frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(deployments_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "karl-brain",
        "model": settings.claude_model,
        "vps_agent": settings.vps_agent_url,
    }


@app.get("/api/conversations")
async def list_conversations():
    """Liste les conversations récentes (stub — à compléter)."""
    return {"conversations": []}


# Servir le frontend React en production
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )
