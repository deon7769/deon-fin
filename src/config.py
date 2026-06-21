from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env.local", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    api_key: str | None
    use_sandbox: bool
    database_url: str
    log_level: str
    # Análise por IA (multi-provedor)
    analyst_provider: str          # anthropic | openrouter | ollama | gemini | zai | openai
    analyst_model: str
    analyst_api_key: str | None
    analyst_base_url: str | None    # None para Anthropic (SDK nativo)
    analyst_max_tokens: int
    monthly_income: float | None
    financial_goals: list[str]
    family_profile: dict[str, Any] | None = None
    # Auto-sync do Pluggy
    auto_sync_minutes: int = 360   # 0 desativa o agendador periódico
    auto_sync_days: int = 30       # quantos dias puxar a cada sync
    auto_sync_on_start: bool = True
    # Login (Basic Auth) — se app_password vazio, autenticação fica DESLIGADA (uso local).
    app_user: str = "familia"
    app_password: str | None = None
    cors_origins: list[str] | None = None

    @property
    def database_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            return PROJECT_ROOT / url.removeprefix("sqlite:///")
        raise ValueError(f"Unsupported DATABASE_URL: {url}")


def load_settings() -> Settings:
    client_id = os.environ.get("PLUGGY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("PLUGGY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(
            "PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET precisam estar definidos no .env"
        )
    income_raw = os.environ.get("MONTHLY_INCOME", "").strip()
    try:
        monthly_income = float(income_raw) if income_raw else None
    except ValueError:
        monthly_income = None
    goals = [g.strip() for g in os.environ.get("FINANCIAL_GOALS", "").split(",") if g.strip()]

    # Carregar perfil familiar se disponível
    family_profile_path = PROJECT_ROOT / "data" / "family_profile.json"
    family_profile = None
    if family_profile_path.exists():
        try:
            with open(family_profile_path, "r", encoding="utf-8") as f:
                family_profile = json.load(f)
        except Exception:
            pass

    # Integrar receitas do perfil se monthly_income não estiver no env
    if not monthly_income and family_profile and "receitas" in family_profile:
        monthly_income = sum(item["valor"] for item in family_profile["receitas"])

    # Integrar metas do perfil se não estiver no env
    if not goals and family_profile and "metas" in family_profile:
        goals = [m["nome"] for m in family_profile["metas"]]

    provider = os.environ.get("ANALYST_PROVIDER", "anthropic").strip().lower()
    # Base URLs (compatíveis com OpenAI) por provedor; Anthropic usa SDK nativo.
    _BASE_URLS = {
        "openrouter": "https://openrouter.ai/api/v1",
        "ollama": "http://localhost:11434/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "zai": "https://api.z.ai/api/paas/v4",
        "openai": "https://api.openai.com/v1",
    }
    _DEFAULT_MODELS = {
        "anthropic": "claude-opus-4-8",
        "openrouter": "anthropic/claude-sonnet-4.5",
        "ollama": "llama3.1:8b",
        "gemini": "gemini-1.5-pro",
        "zai": "glm-4.6",
        "openai": "gpt-4o",
    }
    # Chave: ANALYST_API_KEY genérica, ou a específica do provedor (reaproveita .env existentes).
    _KEY_ENV = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "zai": "ZAI_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    _key_candidates = [
        os.environ.get("ANALYST_API_KEY"),
        os.environ.get(_KEY_ENV.get(provider, "")),
    ]
    if provider == "zai":
        # Aliases comuns para Z.ai (z.api)
        _key_candidates.extend([
            os.environ.get("ZAI_API_KEY"),
            os.environ.get("Z_API_KEY"),
        ])
    analyst_api_key = next((k.strip() for k in _key_candidates if k and k.strip()), None)
    analyst_base_url = os.environ.get("ANALYST_BASE_URL") or _BASE_URLS.get(provider)
    analyst_model = os.environ.get("ANALYST_MODEL") or _DEFAULT_MODELS.get(provider, "")
    try:
        analyst_max_tokens = int(os.environ.get("ANALYST_MAX_TOKENS", "16000"))
    except ValueError:
        analyst_max_tokens = 16000

    return Settings(
        client_id=client_id,
        client_secret=client_secret,
        api_key=os.environ.get("PLUGGY_API_KEY") or None,
        use_sandbox=os.environ.get("PLUGGY_USE_SANDBOX", "true").lower() == "true",
        database_url=os.environ.get("DATABASE_URL", "sqlite:///data/financas.db"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        analyst_provider=provider,
        analyst_model=analyst_model,
        analyst_api_key=analyst_api_key,
        analyst_base_url=analyst_base_url,
        analyst_max_tokens=analyst_max_tokens,
        monthly_income=monthly_income,
        financial_goals=goals,
        family_profile=family_profile,
        auto_sync_minutes=int(os.environ.get("AUTO_SYNC_MINUTES", "360") or 0),
        auto_sync_days=int(os.environ.get("AUTO_SYNC_DAYS", "30") or 30),
        auto_sync_on_start=os.environ.get("AUTO_SYNC_ON_START", "true").lower() == "true",
        app_user=os.environ.get("APP_USER", "familia").strip() or "familia",
        app_password=(os.environ.get("APP_PASSWORD") or "").strip() or None,
        cors_origins=[
            origin.strip()
            for origin in os.environ.get(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ],
    )


settings = load_settings()
