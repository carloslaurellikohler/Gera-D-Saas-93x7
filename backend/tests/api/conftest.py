from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_analysis_service
from app.core.config import Settings
from app.main import app
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisService
from app.storage.local_storage import LocalDiskStorage


@pytest.fixture()
def api_service(db_session, tmp_path: Path) -> AnalysisService:
    settings = Settings(DEFAULT_CS_ID="cs-1", DEFAULT_CS_NAME="Consultor Teste", MAX_UPLOAD_MB=100)
    storage = LocalDiskStorage(tmp_path / "storage")
    engine = MagicMock()
    return AnalysisService(
        repo=AnalysisRepository(db_session), storage=storage, engine=engine, settings=settings
    )


@pytest.fixture()
def client(api_service: AnalysisService, mocker):
    mocker.patch("app.api.routes.analyses.process_analysis_task.delay")

    app.dependency_overrides[get_analysis_service] = lambda: api_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
