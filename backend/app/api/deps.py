from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.engine_integration.adapter import EngineAdapter
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisService
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
