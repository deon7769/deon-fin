from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# .env.local has precedence over .env (use .env.local for real secrets locally,
# .env stays as a committed template)
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
    return Settings(
        client_id=client_id,
        client_secret=client_secret,
        api_key=os.environ.get("PLUGGY_API_KEY") or None,
        use_sandbox=os.environ.get("PLUGGY_USE_SANDBOX", "true").lower() == "true",
        database_url=os.environ.get("DATABASE_URL", "sqlite:///data/financas.db"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
