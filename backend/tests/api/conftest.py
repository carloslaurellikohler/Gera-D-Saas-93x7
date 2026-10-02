from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_analysis_service, get_content_service, get_learning_path_service
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.learning_path_enrollment_repository import LearningPathEnrollmentRepository
from app.repositories.learning_path_repository import LearningPathRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import AnalysisService
from app.services.content_service import ContentService
from app.services.learning_path_service import LearningPathService
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
def content_service(db_session, tmp_path: Path) -> ContentService:
    storage = LocalDiskStorage(tmp_path / "content_storage")
    return ContentService(repo=ContentRepository(db_session), storage=storage, max_upload_mb=10)


@pytest.fixture()
def learning_path_service(db_session) -> LearningPathService:
    return LearningPathService(
        repo=LearningPathRepository(db_session),
        content_repo=ContentRepository(db_session),
        metrics_repo=MetricsRepository(db_session),
        enrollment_repo=LearningPathEnrollmentRepository(db_session),
    )


@pytest.fixture()
def _overrides(api_service, content_service, learning_path_service, db_session, mocker):
    mocker.patch("app.api.routes.analyses.process_analysis_task.delay")
    app.dependency_overrides[get_analysis_service] = lambda: api_service
    app.dependency_overrides[get_content_service] = lambda: content_service
    app.dependency_overrides[get_learning_path_service] = lambda: learning_path_service
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client(_overrides) -> TestClient:
    """Cliente sem login — para testar que as rotas exigem autenticação."""
    return TestClient(app)


@pytest.fixture()
def client_factory(_overrides, db_session):
    """Fábrica de TestClients autenticados — cada chamada cria um usuário novo, faz
    login e devolve (client, user). Usada quando um teste precisa de mais de uma
    identidade (ex.: dono vs. não-dono, usuário comum vs. ADMIN)."""

    def _make(role: UserRole = UserRole.USER, **user_overrides) -> tuple[TestClient, User]:
        defaults = dict(
            name="Usuária Teste",
            email=f"user-{uuid.uuid4()}@example.com",
            password_hash=hash_password("correct-password"),
            role=role,
            status=UserStatus.ACTIVE,
        )
        defaults.update(user_overrides)
        user = UserRepository(db_session).create(User(**defaults))
        test_client = TestClient(app)
        login = test_client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "correct-password"}
        )
        assert login.status_code == 200
        return test_client, user

    return _make


@pytest.fixture()
def client(client_factory) -> TestClient:
    """Cliente autenticado como um usuário comum — usado pela maioria dos testes
    existentes, que operam sobre as próprias análises."""
    test_client, _ = client_factory()
    return test_client


@pytest.fixture()
def admin_client(client_factory) -> TestClient:
    test_client, _ = client_factory(role=UserRole.ADMIN)
    return test_client
