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

    MAX_UPLOAD_MB: int = 1024

    TASK_TIME_LIMIT_SECONDS: int = 3600
    TASK_SOFT_TIME_LIMIT_SECONDS: int = 3300

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    API_V1_PREFIX: str = "/api/v1"

    # --- Autenticação ---
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Bootstrap do primeiro usuário ADMIN (ver backend/scripts/seed_admin.py)
    SEED_ADMIN_EMAIL: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None
    SEED_ADMIN_NAME: str = "Administrador"

    # --- Assistente de IA (Fase 6) — distinto de OPENAI_MODEL/OPENAI_TEMPERATURE da
    # engine (gera_d_engine.config), que usa seu próprio modelo para o pipeline pesado
    # de análise. Reaproveita a mesma OPENAI_API_KEY do ambiente.
    OPENAI_API_KEY: str | None = None
    ASSISTANT_CHAT_MODEL: str = "gpt-6-luna"
    ASSISTANT_CHAT_TEMPERATURE: float = 0.3
    ASSISTANT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    ASSISTANT_DAILY_MESSAGE_LIMIT: int = 30
    ASSISTANT_HISTORY_WINDOW: int = 10
    ASSISTANT_TOP_K_CHUNKS: int = 4
    ASSISTANT_CHUNK_SIZE: int = 1200
    ASSISTANT_CHUNK_OVERLAP: int = 200

    # --- FinAI: observabilidade de custo de IA ---
    # Preço por modelo, orçamento mensal e taxa USD→BRL NÃO vivem aqui: são editáveis pelo
    # ADMIN na tela, no banco (ai_model_prices / ai_cost_budgets / ai_cost_settings). Aqui
    # fica só o que é operacional. AI_COST_TRACKING_ENABLED é kill switch: com false, a
    # captura é desligada inteira sem precisar reverter código.
    AI_COST_TRACKING_ENABLED: bool = True
    AI_COST_FFPROBE_TIMEOUT_SECONDS: int = 60

    # Limitador diário de análises por colaborador (owner_id) — controle de custo/fluxo.
    # ADMIN é isento quando sobe para si mesmo; GESTOR nunca é isento (o limite é do
    # colaborador avaliado, não de quem faz upload). Reset à meia-noite UTC.
    DAILY_ANALYSIS_LIMIT_PER_OWNER: int = 4


def get_settings() -> Settings:
    return Settings()
