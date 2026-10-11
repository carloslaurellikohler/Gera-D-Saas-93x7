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
    assert fetched.role == UserRole.COLABORADOR
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
    repo.create(_new_user(email="user@example.com", role=UserRole.COLABORADOR))

    admins = repo.list(role=UserRole.ADMIN)

    assert [row.User.email for row in admins] == ["admin@example.com"]


def test_list_filters_by_status(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(email="active@example.com"))
    repo.create(_new_user(email="inactive@example.com", status=UserStatus.INACTIVE))

    inactive = repo.list(status=UserStatus.INACTIVE)

    assert [row.User.email for row in inactive] == ["inactive@example.com"]


def test_list_filters_by_search_matches_name_or_email(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(name="Ana Souza", email="ana@example.com"))
    repo.create(_new_user(name="Bruno Lima", email="bruno@example.com"))

    by_name = repo.list(search="ana")
    by_email = repo.list(search="bruno@example")

    assert [row.User.email for row in by_name] == ["ana@example.com"]
    assert [row.User.email for row in by_email] == ["bruno@example.com"]


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

    assert [row.User.name for row in result] == ["Ana", "Zeca"]


def test_list_includes_manager_name_for_colaborador(db_session):
    repo = UserRepository(db_session)
    gestor = repo.create(_new_user(name="Gestor", email="gestor4@example.com", role=UserRole.GESTOR))
    repo.create(
        _new_user(
            name="Colaborador", email="colab4@example.com", role=UserRole.COLABORADOR, manager_id=gestor.id
        )
    )
    repo.create(_new_user(name="Sem gestor", email="solta4@example.com", role=UserRole.COLABORADOR))

    result = {row.User.email: row.manager_name for row in repo.list()}

    assert result["colab4@example.com"] == "Gestor"
    assert result["solta4@example.com"] is None


def test_list_includes_team_size_for_gestor(db_session):
    repo = UserRepository(db_session)
    gestor = repo.create(_new_user(name="Gestor", email="gestor5@example.com", role=UserRole.GESTOR))
    repo.create(_new_user(name="Gestor Vazio", email="gestor6@example.com", role=UserRole.GESTOR))
    repo.create(
        _new_user(
            name="Colaborador1", email="colab5@example.com", role=UserRole.COLABORADOR, manager_id=gestor.id
        )
    )
    repo.create(
        _new_user(
            name="Colaborador2", email="colab6@example.com", role=UserRole.COLABORADOR, manager_id=gestor.id
        )
    )

    result = {row.User.email: row.team_size for row in repo.list()}

    assert result["gestor5@example.com"] == 2
    assert result["gestor6@example.com"] == 0
    assert result["colab5@example.com"] == 0


def test_list_filters_by_manager_id(db_session):
    repo = UserRepository(db_session)
    gestor1 = repo.create(_new_user(name="Gestor1", email="gestor7@example.com", role=UserRole.GESTOR))
    gestor2 = repo.create(_new_user(name="Gestor2", email="gestor8@example.com", role=UserRole.GESTOR))
    repo.create(
        _new_user(
            name="Colaborador1", email="colab7@example.com", role=UserRole.COLABORADOR, manager_id=gestor1.id
        )
    )
    repo.create(
        _new_user(
            name="Colaborador2", email="colab8@example.com", role=UserRole.COLABORADOR, manager_id=gestor2.id
        )
    )

    result = repo.list(manager_id=gestor1.id)

    assert [row.User.email for row in result] == ["colab7@example.com"]


def test_list_subordinates_returns_only_direct_reports(db_session):
    repo = UserRepository(db_session)
    gestor = repo.create(_new_user(name="Gestor", email="gestor@example.com", role=UserRole.GESTOR))
    repo.create(
        _new_user(name="Zeca", email="zeca2@example.com", role=UserRole.COLABORADOR, manager_id=gestor.id)
    )
    repo.create(
        _new_user(name="Ana", email="ana3@example.com", role=UserRole.COLABORADOR, manager_id=gestor.id)
    )
    repo.create(_new_user(name="Sem gestor", email="solta@example.com"))

    result = repo.list_subordinates(gestor.id)

    assert [u.name for u in result] == ["Ana", "Zeca"]
