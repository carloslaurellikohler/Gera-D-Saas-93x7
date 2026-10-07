from __future__ import annotations

import uuid

from app.models.user import UserRole


def test_list_users_requires_admin(client):
    response = client.get("/api/v1/users")

    assert response.status_code == 403


def test_list_users_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/users")

    assert response.status_code == 401


def test_list_users_as_admin(admin_client):
    response = admin_client.get("/api/v1/users")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_user_as_admin(admin_client):
    response = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_create_user_rejects_duplicate_email(admin_client):
    payload = {
        "name": "Ana Souza",
        "email": "ana@example.com",
        "password": "correct-password",
        "role": "COLABORADOR",
    }
    admin_client.post("/api/v1/users", json=payload)

    response = admin_client.post("/api/v1/users", json=payload)

    assert response.status_code == 409


def test_create_user_rejects_short_password(admin_client):
    response = admin_client.post(
        "/api/v1/users",
        json={"name": "Ana Souza", "email": "ana@example.com", "password": "short", "role": "COLABORADOR"},
    )

    assert response.status_code == 422


def test_create_user_requires_admin(client):
    response = client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    )

    assert response.status_code == 403


def test_update_user_as_admin(admin_client):
    created = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()

    response = admin_client.put(
        f"/api/v1/users/{created['id']}",
        json={"name": "Ana Souza Lima", "email": "ana.lima@example.com", "role": "ADMIN"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Ana Souza Lima"
    assert body["role"] == "ADMIN"


def test_update_user_not_found(admin_client):
    response = admin_client.put(
        f"/api/v1/users/{uuid.uuid4()}",
        json={"name": "X", "email": "x@example.com", "role": "COLABORADOR"},
    )

    assert response.status_code == 404


def test_update_user_rejects_email_collision(admin_client):
    admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    )
    bruno = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Bruno Lima",
            "email": "bruno@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()

    response = admin_client.put(
        f"/api/v1/users/{bruno['id']}",
        json={"name": "Bruno Lima", "email": "ana@example.com", "role": "COLABORADOR"},
    )

    assert response.status_code == 409


def test_deactivate_and_activate_another_user(admin_client):
    target = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()

    deactivate_response = admin_client.post(f"/api/v1/users/{target['id']}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "INACTIVE"

    activate_response = admin_client.post(f"/api/v1/users/{target['id']}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["status"] == "ACTIVE"


def test_deactivated_user_cannot_login(admin_client):
    target = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()
    admin_client.post(f"/api/v1/users/{target['id']}/deactivate")

    login_response = admin_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "correct-password"}
    )

    assert login_response.status_code == 403


def test_deactivate_not_found(admin_client):
    response = admin_client.post(f"/api/v1/users/{uuid.uuid4()}/deactivate")

    assert response.status_code == 404


def test_admin_cannot_deactivate_self(client_factory):
    admin_test_client, admin_user = client_factory(role=UserRole.ADMIN)

    response = admin_test_client.post(f"/api/v1/users/{admin_user.id}/deactivate")

    assert response.status_code == 409


def test_deactivate_requires_admin(client, client_factory):
    _, target_user = client_factory(role=UserRole.COLABORADOR)

    response = client.post(f"/api/v1/users/{target_user.id}/deactivate")

    assert response.status_code == 403


def test_reset_password_as_admin(admin_client):
    target = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()

    response = admin_client.post(
        f"/api/v1/users/{target['id']}/reset-password", json={"password": "new-password-123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert "password" not in body
    assert "password_hash" not in body


def test_reset_password_changes_login_credentials(admin_client):
    target = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()
    admin_client.post(
        f"/api/v1/users/{target['id']}/reset-password", json={"password": "new-password-123"}
    )

    old_password_login = admin_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "correct-password"}
    )
    new_password_login = admin_client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "new-password-123"}
    )

    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200


def test_reset_password_rejects_short_password(admin_client):
    target = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
        },
    ).json()

    response = admin_client.post(
        f"/api/v1/users/{target['id']}/reset-password", json={"password": "short"}
    )

    assert response.status_code == 422


def test_reset_password_not_found(admin_client):
    response = admin_client.post(
        f"/api/v1/users/{uuid.uuid4()}/reset-password", json={"password": "new-password-123"}
    )

    assert response.status_code == 404


def test_reset_password_requires_admin(client, client_factory):
    _, target_user = client_factory(role=UserRole.COLABORADOR)

    response = client.post(
        f"/api/v1/users/{target_user.id}/reset-password", json={"password": "new-password-123"}
    )

    assert response.status_code == 403


def test_reset_password_requires_auth(unauthenticated_client, client_factory):
    _, target_user = client_factory(role=UserRole.COLABORADOR)

    response = unauthenticated_client.post(
        f"/api/v1/users/{target_user.id}/reset-password", json={"password": "new-password-123"}
    )

    assert response.status_code == 401


def test_list_my_team_as_gestor_retorna_so_subordinados(client_factory):
    gestor_client, gestor = client_factory(role=UserRole.GESTOR)
    _, colaborador = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)
    client_factory(role=UserRole.COLABORADOR)  # outro colaborador, sem gestor

    response = gestor_client.get("/api/v1/users/me/team")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(colaborador.id)


def test_list_my_team_requires_gestor(client):
    response = client.get("/api/v1/users/me/team")

    assert response.status_code == 403


def test_create_colaborador_com_manager_id_valido(admin_client, client_factory):
    _, gestor = client_factory(role=UserRole.GESTOR)

    response = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
            "manager_id": str(gestor.id),
        },
    )

    assert response.status_code == 201
    assert response.json()["manager_id"] == str(gestor.id)


def test_create_colaborador_com_manager_id_de_nao_gestor_rejeitado(admin_client, client_factory):
    _, outro_colaborador = client_factory(role=UserRole.COLABORADOR)

    response = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "COLABORADOR",
            "manager_id": str(outro_colaborador.id),
        },
    )

    assert response.status_code == 422


def test_create_gestor_com_manager_id_rejeitado(admin_client, client_factory):
    _, outro_gestor = client_factory(role=UserRole.GESTOR)

    response = admin_client.post(
        "/api/v1/users",
        json={
            "name": "Ana Souza",
            "email": "ana@example.com",
            "password": "correct-password",
            "role": "GESTOR",
            "manager_id": str(outro_gestor.id),
        },
    )

    assert response.status_code == 422


def test_despromover_gestor_com_equipe_retorna_409(admin_client, client_factory):
    _, gestor = client_factory(role=UserRole.GESTOR)
    client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    response = admin_client.put(
        f"/api/v1/users/{gestor.id}",
        json={"name": gestor.name, "email": gestor.email, "role": "COLABORADOR"},
    )

    assert response.status_code == 409


def test_desativar_gestor_com_equipe_retorna_409(admin_client, client_factory):
    _, gestor = client_factory(role=UserRole.GESTOR)
    client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    response = admin_client.post(f"/api/v1/users/{gestor.id}/deactivate")

    assert response.status_code == 409
