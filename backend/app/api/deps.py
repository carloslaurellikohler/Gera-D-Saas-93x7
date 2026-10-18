from __future__ import annotations

import uuid
from collections.abc import Generator

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai_cost.recorder import get_usage_sink
from app.core.config import Settings, get_settings
from app.core.security import ACCESS_TOKEN_COOKIE, decode_access_token
from app.db.session import get_db
from app.engine_integration.adapter import EngineAdapter, NoPublishedMethodologyError
from app.models.user import User, UserRole, UserStatus
from app.repositories.ai_cost_config_repository import AiCostConfigRepository
from app.repositories.ai_cost_repository import AiCostRepository
from app.repositories.ai_price_repository import AiPriceRepository
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.learning_path_enrollment_repository import LearningPathEnrollmentRepository
from app.repositories.learning_path_repository import LearningPathRepository
from app.repositories.methodology_chunk_repository import MethodologyChunkRepository
from app.repositories.methodology_repository import MethodologyRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.runtime_settings_repository import RuntimeSettingsRepository
from app.repositories.user_repository import UserRepository
from app.services.ai_cost_service import AiCostService
from app.services.analysis_service import AnalysisService
from app.services.assistant_service import AssistantService
from app.services.auth_service import AuthService
from app.services.content_service import ContentService
from app.services.dashboard_service import DashboardService
from app.services.learning_path_service import LearningPathService
from app.services.methodology_service import MethodologyService
from app.services.metrics_service import MetricsService
from app.services.runtime_settings_service import (
    RuntimeSettingsService,
    build_effective_settings,
)
from app.services.user_service import UserService
from app.storage.local_storage import LocalDiskStorage


def get_effective_settings(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> Settings:
    """Settings do ambiente com os seis campos de runtime_settings sobrepostos — o banco
    sempre vence (ver app/models/runtime_settings.py).

    Relê o banco a cada request, de propósito: é a mesma política de
    EngineAdapter.from_published, que também não cacheia configuração. Trocar o modelo ou um
    limite na tela passa a valer na próxima request, sem reload de processo.
    """
    return build_effective_settings(settings, RuntimeSettingsRepository(db).get())


def get_analysis_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_effective_settings)
) -> AnalysisService:
    try:
        engine = EngineAdapter.from_published(db)
    except NoPublishedMethodologyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return AnalysisService(
        repo=AnalysisRepository(db),
        storage=LocalDiskStorage(settings.STORAGE_DIR),
        engine=engine,
        settings=settings,
        usage_sink=get_usage_sink(),
    )


def get_ai_cost_service(db: Session = Depends(get_db)) -> AiCostService:
    return AiCostService(
        repo=AiCostRepository(db),
        price_repo=AiPriceRepository(db),
        config_repo=AiCostConfigRepository(db),
        usage_repo=AiUsageRepository(db),
    )


def get_auth_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> AuthService:
    return AuthService(repo=UserRepository(db), settings=settings)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(repo=UserRepository(db))


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(
        repo=DashboardRepository(db),
        methodology_repo=MethodologyRepository(db),
        user_repo=UserRepository(db),
    )


def get_methodology_service(db: Session = Depends(get_db)) -> MethodologyService:
    return MethodologyService(repo=MethodologyRepository(db))


def get_metrics_service(db: Session = Depends(get_db)) -> MetricsService:
    return MetricsService(repo=MetricsRepository(db), user_repo=UserRepository(db))


def get_content_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> ContentService:
    return ContentService(
        repo=ContentRepository(db),
        storage=LocalDiskStorage(settings.STORAGE_DIR),
        max_upload_mb=settings.MAX_UPLOAD_MB,
    )


def get_learning_path_service(db: Session = Depends(get_db)) -> LearningPathService:
    return LearningPathService(
        repo=LearningPathRepository(db),
        content_repo=ContentRepository(db),
        metrics_repo=MetricsRepository(db),
        enrollment_repo=LearningPathEnrollmentRepository(db),
    )


def get_assistant_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_effective_settings)
) -> AssistantService:
    return AssistantService(
        chat_repo=ChatMessageRepository(db),
        chunk_repo=MethodologyChunkRepository(db),
        metrics_repo=MetricsRepository(db),
        user_repo=UserRepository(db),
        settings=settings,
        usage_sink=get_usage_sink(),
    )


def get_runtime_settings_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> RuntimeSettingsService:
    # Recebe o Settings do ambiente (não o efetivo): este service é justamente quem resolve a
    # sobreposição, e precisa do bootstrap puro como fallback quando a linha não existe.
    return RuntimeSettingsService(
        repo=RuntimeSettingsRepository(db),
        user_repo=UserRepository(db),
        price_repo=AiPriceRepository(db),
        settings=settings,
    )


def get_current_user(
    token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")
    try:
        payload = decode_access_token(token, settings)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada."
        )

    user = UserRepository(db).get(uuid.UUID(payload["sub"]))
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida.")
    return user


def require_role(*roles: UserRole):
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não permitido.")
        return user

    return _dependency
