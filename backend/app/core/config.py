"""Configuração da aplicação backend, via variáveis de ambiente.

Distinta da Settings da engine (gera_d_engine.config) — esta cobre banco, fila,
storage e defaults de negócio do SaaS, não parâmetros do motor de IA.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://gerad:gerad@localhost:5432/gerad"
    REDIS_URL: str = "redis://localhost:6379/0"

    STORAGE_DIR: str = "./storage_data"

    DEFAULT_CS_ID: str = "cs-padrao"
    DEFAULT_CS_NAME: str = "Consultor GerAD"

    MAX_UPLOAD_MB: int = 100

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    API_V1_PREFIX: str = "/api/v1"


def get_settings() -> Settings:
    return Settings()
