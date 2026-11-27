"""Application settings from environment placeholders."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Invoice AI"
    app_env: str = "development"
    debug: bool = True
    app_version: str = "0.6.0-m6"

    api_host: str = "0.0.0.0"
    api_port: int = 8004
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3004"

    database_url: str = (
        "postgresql+psycopg://invoiceai:invoiceai_dev_password@localhost:5436/invoice_ai"
    )

    demo_user_email: str = "demo@invoiceai.local"
    demo_user_password: str = "demo"
    secret_key: str = "change-me-local-dev-only-32b-min"
    access_token_expire_minutes: int = 60
    # Minimum password length when APP_ENV=production (demo accounts exempt in non-prod)
    password_min_length: int = 8

    # Insights connector shared token (optional alternative to org JWT)
    insights_connector_token: str = ""

    # In-memory rate limits (per process)
    auth_rate_limit: int = 20
    auth_rate_window_seconds: int = 60
    ai_rate_limit: int = 60
    ai_rate_window_seconds: int = 60

    ai_provider: str = "demo"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    @property
    def is_demo_or_dev(self) -> bool:
        return self.app_env.strip().lower() in {
            "development",
            "dev",
            "demo",
            "test",
            "local",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_production_secrets(settings: Settings | None = None) -> None:
    """Refuse weak secrets / debug when APP_ENV is production."""
    s = settings or get_settings()
    if not s.is_production:
        return
    weak_keys = {
        "",
        "change-me-local-dev-only-32b-min",
        "test-secret-key-invoice-ai-m1-32b",
        "secret",
        "changeme",
    }
    if s.secret_key.strip() in weak_keys or len(s.secret_key.strip()) < 32:
        raise RuntimeError(
            "APP_ENV=production requires a strong SECRET_KEY "
            "(at least 32 characters, not a documented demo default)."
        )
    if s.debug:
        raise RuntimeError("APP_ENV=production requires DEBUG=false.")
