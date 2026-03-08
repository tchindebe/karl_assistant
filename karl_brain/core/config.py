"""
Configuration centralisée via Pydantic Settings.
Charge depuis .env automatiquement.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Provider LLM ──────────────────────────────────────────────────────────
    provider: str = Field("anthropic", env="PROVIDER")

    # ─── Anthropic / Claude ────────────────────────────────────────────────────
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-opus-4-6", env="CLAUDE_MODEL")

    # ─── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", env="OPENAI_MODEL")
    openai_base_url: str = Field("", env="OPENAI_BASE_URL")

    # ─── Ollama (local, OpenAI-compatible) ────────────────────────────────────
    ollama_base_url: str = Field("http://localhost:11434/v1", env="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3.1", env="OLLAMA_MODEL")

    # ─── Google Gemini ─────────────────────────────────────────────────────────
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.0-flash", env="GEMINI_MODEL")

    # ─── VPS Agent ─────────────────────────────────────────────────────────────
    vps_agent_url: str = Field("http://localhost:8001", env="VPS_AGENT_URL")
    vps_agent_api_key: str = Field(..., env="VPS_AGENT_API_KEY")
    vps_agent_timeout: int = Field(120, env="VPS_AGENT_TIMEOUT")

    # ─── Auth ──────────────────────────────────────────────────────────────────
    karl_admin_password: str = Field(..., env="KARL_ADMIN_PASSWORD")
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(24, env="JWT_EXPIRE_HOURS")

    # ─── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field("sqlite+aiosqlite:///./karl.db", env="DATABASE_URL")

    # ─── Notifications ─────────────────────────────────────────────────────────
    telegram_bot_token: str = Field("", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", env="TELEGRAM_CHAT_ID")
    slack_webhook_url: str = Field("", env="SLACK_WEBHOOK_URL")
    smtp_host: str = Field("", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: str = Field("", env="SMTP_USER")
    smtp_password: str = Field("", env="SMTP_PASSWORD")
    smtp_from: str = Field("", env="SMTP_FROM")
    notification_email_to: str = Field("", env="NOTIFICATION_EMAIL_TO")
    notification_webhook_url: str = Field("", env="NOTIFICATION_WEBHOOK_URL")

    # ─── Monitoring ────────────────────────────────────────────────────────────
    monitor_interval_seconds: int = Field(60, env="MONITOR_INTERVAL_SECONDS")
    alert_cpu_warning: float = Field(80.0, env="ALERT_CPU_WARNING")
    alert_cpu_critical: float = Field(95.0, env="ALERT_CPU_CRITICAL")
    alert_ram_warning: float = Field(85.0, env="ALERT_RAM_WARNING")
    alert_ram_critical: float = Field(95.0, env="ALERT_RAM_CRITICAL")
    alert_disk_warning: float = Field(80.0, env="ALERT_DISK_WARNING")
    alert_disk_critical: float = Field(90.0, env="ALERT_DISK_CRITICAL")
    daily_report_enabled: bool = Field(True, env="DAILY_REPORT_ENABLED")
    daily_report_hour: int = Field(8, env="DAILY_REPORT_HOUR")

    # ─── Auto-healing ──────────────────────────────────────────────────────────
    healing_interval_seconds: int = Field(30, env="HEALING_INTERVAL_SECONDS")
    healing_enabled: bool = Field(True, env="HEALING_ENABLED")

    # ─── CI/CD Webhooks ────────────────────────────────────────────────────────
    github_webhook_secret: str = Field("", env="GITHUB_WEBHOOK_SECRET")
    gitlab_webhook_secret: str = Field("", env="GITLAB_WEBHOOK_SECRET")
    ci_deploy_branches_raw: str = Field("main,production", env="CI_DEPLOY_BRANCHES")

    @property
    def ci_deploy_branches(self) -> List[str]:
        return [b.strip() for b in self.ci_deploy_branches_raw.split(",")]

    # ─── DNS / Cloudflare ──────────────────────────────────────────────────────
    cloudflare_api_token: str = Field("", env="CLOUDFLARE_API_TOKEN")
    cloudflare_zone_id: str = Field("", env="CLOUDFLARE_ZONE_ID")

    # ─── Odoo CRM (optionnel) ──────────────────────────────────────────────────
    odoo_url: str = Field("", env="ODOO_URL")
    odoo_db: str = Field("", env="ODOO_DB")
    odoo_username: str = Field("", env="ODOO_USERNAME")
    odoo_api_key: str = Field("", env="ODOO_API_KEY")

    # ─── Analytics (optionnel) ─────────────────────────────────────────────────
    ga4_property_id: str = Field("", env="GA4_PROPERTY_ID")
    ga4_credentials_json: str = Field("", env="GA4_CREDENTIALS_JSON")
    plausible_api_key: str = Field("", env="PLAUSIBLE_API_KEY")
    plausible_site_id: str = Field("", env="PLAUSIBLE_SITE_ID")

    # ─── App ───────────────────────────────────────────────────────────────────
    app_port: int = Field(8000, env="APP_PORT")
    debug: bool = Field(False, env="DEBUG")
    cors_origins: str = Field("http://localhost:5173,http://localhost:3000", env="CORS_ORIGINS")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
