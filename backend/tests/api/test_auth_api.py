from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def auth_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db_session, **overrides) -> User:
    defaults = dict(
        name="Ana Souza",
        email="ana@example.com",
        password_hash=hash_password("correct-password"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    defaults.update(overrides)
    return UserRepository(db_session).create(User(**defaults))


def test_login_success_sets_cookie(db_session, auth_client):
    _create_user(db_session)

    response = auth_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "correct-password"}
    )

    assert response.status_code == 200
    assert "gerad_access_token" in response.cookies
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert "password_hash" not in body


def test_login_wrong_password(db_session, auth_client):
    _create_user(db_session)

    response = auth_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_inactive_user(db_session, auth_client):
    _create_user(db_session, email="inativo@example.com", status=UserStatus.INACTIVE)

    response = auth_client.post(
        "/api/v1/auth/login", json={"email": "inativo@example.com", "password": "correct-password"}
    )

    assert response.status_code == 403


def test_me_without_cookie(auth_client):
    response = auth_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_with_cookie(db_session, auth_client):
    _create_user(db_session)
    auth_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "correct-password"}
    )

    response = auth_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"


def test_logout_clears_cookie(db_session, auth_client):
    _create_user(db_session)
    auth_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "correct-password"}
    )

    logout_response = auth_client.post("/api/v1/auth/logout")
    me_response = auth_client.get("/api/v1/auth/me")

    assert logout_response.status_code == 204
    assert me_response.status_code == 401
