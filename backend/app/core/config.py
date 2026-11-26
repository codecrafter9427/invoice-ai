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

    ai_provider: str = "demo"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
