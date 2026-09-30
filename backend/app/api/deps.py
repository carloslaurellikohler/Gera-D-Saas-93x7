from __future__ import annotations

import uuid
from collections.abc import Generator

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import ACCESS_TOKEN_COOKIE, decode_access_token
from app.db.session import get_db
from app.engine_integration.adapter import EngineAdapter
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import AnalysisService
from app.services.auth_service import AuthService
from app.storage.local_storage import LocalDiskStorage


def get_analysis_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> AnalysisService:
    return AnalysisService(
        repo=AnalysisRepository(db),
        storage=LocalDiskStorage(settings.STORAGE_DIR),
        engine=EngineAdapter(),
        settings=settings,
    )


def get_auth_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> AuthService:
    return AuthService(repo=UserRepository(db), settings=settings)


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
