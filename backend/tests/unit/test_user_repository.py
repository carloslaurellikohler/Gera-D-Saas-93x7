from __future__ import annotations

from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


def _new_user(**overrides) -> User:
    defaults = dict(
        name="Ana Souza",
        email="ana@example.com",
        password_hash="hashed-value",
    )
    defaults.update(overrides)
    return User(**defaults)


def test_create_and_get(db_session):
    repo = UserRepository(db_session)
    created = repo.create(_new_user())

    fetched = repo.get(created.id)

    assert fetched is not None
    assert fetched.email == "ana@example.com"
    assert fetched.role == UserRole.USER
    assert fetched.status == UserStatus.ACTIVE
    assert fetched.created_at is not None


def test_get_by_email(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(email="bruno@example.com"))

    found = repo.get_by_email("bruno@example.com")
    missing = repo.get_by_email("nao-existe@example.com")

    assert found is not None
    assert found.email == "bruno@example.com"
    assert missing is None


def test_update(db_session):
    repo = UserRepository(db_session)
    created = repo.create(_new_user(email="carla@example.com"))

    updated = repo.update(created.id, status=UserStatus.INACTIVE)

    assert updated.status == UserStatus.INACTIVE


def test_list_filters_by_role(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(email="admin@example.com", role=UserRole.ADMIN))
    repo.create(_new_user(email="user@example.com", role=UserRole.USER))

    admins = repo.list(role=UserRole.ADMIN)

    assert [u.email for u in admins] == ["admin@example.com"]


def test_list_filters_by_status(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(email="active@example.com"))
    repo.create(_new_user(email="inactive@example.com", status=UserStatus.INACTIVE))

    inactive = repo.list(status=UserStatus.INACTIVE)

    assert [u.email for u in inactive] == ["inactive@example.com"]


def test_list_filters_by_search_matches_name_or_email(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(name="Ana Souza", email="ana@example.com"))
    repo.create(_new_user(name="Bruno Lima", email="bruno@example.com"))

    by_name = repo.list(search="ana")
    by_email = repo.list(search="bruno@example")

    assert [u.email for u in by_name] == ["ana@example.com"]
    assert [u.email for u in by_email] == ["bruno@example.com"]


def test_list_combines_filters_and_returns_empty_when_no_match(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(email="admin@example.com", role=UserRole.ADMIN))

    result = repo.list(role=UserRole.ADMIN, status=UserStatus.INACTIVE)

    assert result == []


def test_list_orders_by_name(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(name="Zeca", email="zeca@example.com"))
    repo.create(_new_user(name="Ana", email="ana2@example.com"))

    result = repo.list()

    assert [u.name for u in result] == ["Ana", "Zeca"]
