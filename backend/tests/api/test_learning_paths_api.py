from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.analysis import Analysis, AnalysisStatus
from app.repositories.analysis_repository import AnalysisRepository


def _seed_completed_with_weak_criterion(db_session, *, user_id, criterion_key: str):
    all_scores = {
        "posicionamento": 9.0,
        "conexao": 9.0,
        "sondagem": 9.0,
        "direcionamento": 9.0,
        "encaminhamento": 9.0,
        "eficiencia_conducao": 9.0,
    }
    all_scores[criterion_key] = 3.0
    analysis_result = {
        "overall_score": 7.0,
        "overall_band_label": "Atenção",
        "pilar_93_score": {"key": "pilar_93", "label": "Pilar 93", "score": 7.0},
        "pilar_7_score": {"key": "pilar_7", "label": "Pilar 7", "score": 7.0},
        "scores_by_criterion": [{"key": k, "label": k, "score": v} for k, v in all_scores.items()],
    }
    AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id=f"lp-{uuid.uuid4()}",
            owner_id=user_id,
            status=AnalysisStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            analysis_result=analysis_result,
        )
    )


def test_create_learning_path_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.post("/api/v1/learning-paths", json={"title": "T"})
    assert response.status_code == 401


def test_regular_user_cannot_create_learning_path(client):
    response = client.post("/api/v1/learning-paths", json={"title": "T"})
    assert response.status_code == 403


def test_admin_can_create_learning_path_with_items(admin_client):
    content = admin_client.post(
        "/api/v1/content",
        data={"title": "Material", "kind": "LINK", "external_url": "https://example.com"},
    ).json()

    response = admin_client.post(
        "/api/v1/learning-paths",
        json={
            "title": "Sondagem consultiva",
            "criterion_key": "sondagem",
            "items": [{"content_id": content["id"], "order_index": 0}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Sondagem consultiva"
    assert len(body["items"]) == 1
    assert body["items"][0]["content"]["id"] == content["id"]


def test_create_learning_path_rejects_unknown_content_id(admin_client):
    response = admin_client.post(
        "/api/v1/learning-paths",
        json={"title": "Inválida", "items": [{"content_id": str(uuid.uuid4()), "order_index": 0}]},
    )
    assert response.status_code == 422


def test_list_learning_paths_empty_returns_200(client):
    response = client.get("/api/v1/learning-paths")
    assert response.status_code == 200
    assert response.json() == []


def test_get_learning_path_not_found(client):
    response = client.get(f"/api/v1/learning-paths/{uuid.uuid4()}")
    assert response.status_code == 404


def test_recommended_without_completed_analyses_returns_empty(client):
    response = client.get("/api/v1/learning-paths/recommended")
    assert response.status_code == 200
    assert response.json() == []


def test_recommended_matches_weak_criterion(client_factory, admin_client, db_session):
    owner_client, owner = client_factory()
    _seed_completed_with_weak_criterion(db_session, user_id=owner.id, criterion_key="sondagem")
    admin_client.post(
        "/api/v1/learning-paths", json={"title": "Trilha Sondagem", "criterion_key": "sondagem"}
    )

    response = owner_client.get("/api/v1/learning-paths/recommended")

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert "Trilha Sondagem" in titles


def test_delete_learning_path_requires_admin(client, admin_client):
    created = admin_client.post("/api/v1/learning-paths", json={"title": "Trilha"}).json()

    response = client.delete(f"/api/v1/learning-paths/{created['id']}")
    assert response.status_code == 403


def test_admin_can_delete_learning_path(admin_client):
    created = admin_client.post("/api/v1/learning-paths", json={"title": "Trilha"}).json()

    response = admin_client.delete(f"/api/v1/learning-paths/{created['id']}")

    assert response.status_code == 204
    assert admin_client.get(f"/api/v1/learning-paths/{created['id']}").status_code == 404


def test_update_learning_path_requires_authentication(unauthenticated_client, admin_client):
    created = admin_client.post("/api/v1/learning-paths", json={"title": "Trilha"}).json()

    response = unauthenticated_client.put(
        f"/api/v1/learning-paths/{created['id']}", json={"title": "Atualizada"}
    )
    assert response.status_code == 401


def test_regular_user_cannot_update_learning_path(client, admin_client):
    created = admin_client.post("/api/v1/learning-paths", json={"title": "Trilha"}).json()

    response = client.put(f"/api/v1/learning-paths/{created['id']}", json={"title": "Atualizada"})
    assert response.status_code == 403


def test_update_learning_path_not_found(admin_client):
    response = admin_client.put(
        f"/api/v1/learning-paths/{uuid.uuid4()}", json={"title": "Atualizada"}
    )
    assert response.status_code == 404


def test_update_learning_path_rejects_unknown_content_id(admin_client):
    created = admin_client.post("/api/v1/learning-paths", json={"title": "Trilha"}).json()

    response = admin_client.put(
        f"/api/v1/learning-paths/{created['id']}",
        json={"title": "Atualizada", "items": [{"content_id": str(uuid.uuid4()), "order_index": 0}]},
    )
    assert response.status_code == 422


def test_admin_can_update_learning_path_metadata_and_items(admin_client):
    content_a = admin_client.post(
        "/api/v1/content",
        data={"title": "Material A", "kind": "LINK", "external_url": "https://a.example"},
    ).json()
    content_b = admin_client.post(
        "/api/v1/content",
        data={"title": "Material B", "kind": "LINK", "external_url": "https://b.example"},
    ).json()
    created = admin_client.post(
        "/api/v1/learning-paths",
        json={
            "title": "Original",
            "items": [{"content_id": content_a["id"], "order_index": 0}],
        },
    ).json()

    response = admin_client.put(
        f"/api/v1/learning-paths/{created['id']}",
        json={
            "title": "Atualizada",
            "criterion_key": "conexao",
            "items": [{"content_id": content_b["id"], "order_index": 0}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Atualizada"
    assert body["criterion_key"] == "conexao"
    assert len(body["items"]) == 1
    assert body["items"][0]["content"]["id"] == content_b["id"]

    fetched = admin_client.get(f"/api/v1/learning-paths/{created['id']}").json()
    assert fetched["title"] == "Atualizada"
    assert len(fetched["items"]) == 1


def _create_path_with_items(admin_client, *, item_count: int = 2) -> dict:
    content_ids = [
        admin_client.post(
            "/api/v1/content",
            data={"title": f"Material {i}", "kind": "LINK", "external_url": "https://example.com"},
        ).json()["id"]
        for i in range(item_count)
    ]
    return admin_client.post(
        "/api/v1/learning-paths",
        json={
            "title": "Trilha com itens",
            "items": [{"content_id": cid, "order_index": i} for i, cid in enumerate(content_ids)],
        },
    ).json()


def test_enroll_requires_authentication(unauthenticated_client, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)

    response = unauthenticated_client.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    assert response.status_code == 401


def test_enroll_unknown_path_returns_404(client):
    response = client.post(f"/api/v1/learning-paths/{uuid.uuid4()}/enroll")
    assert response.status_code == 404


def test_enroll_is_idempotent_returns_200_both_times(client, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)

    first = client.post(f"/api/v1/learning-paths/{path['id']}/enroll")
    second = client.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    assert first.status_code == 200
    assert second.status_code == 200


def test_list_enrolled_empty_returns_200_empty_list(client):
    response = client.get("/api/v1/learning-paths/enrolled")
    assert response.status_code == 200
    assert response.json() == []


def test_list_enrolled_after_enrolling_shows_path(client, admin_client):
    path = _create_path_with_items(admin_client, item_count=2)
    client.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    response = client.get("/api/v1/learning-paths/enrolled")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == path["id"]
    assert body[0]["progress_percent"] == 0.0
    assert body[0]["is_completed"] is False


def test_complete_item_without_enrollment_returns_409(client, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)
    item_id = path["items"][0]["id"]

    response = client.post(f"/api/v1/learning-paths/{path['id']}/items/{item_id}/complete")

    assert response.status_code == 409


def test_complete_item_requires_authentication(unauthenticated_client, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)
    item_id = path["items"][0]["id"]

    response = unauthenticated_client.post(f"/api/v1/learning-paths/{path['id']}/items/{item_id}/complete")

    assert response.status_code == 401


def test_complete_unknown_item_returns_404(client, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)
    client.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    response = client.post(f"/api/v1/learning-paths/{path['id']}/items/{uuid.uuid4()}/complete")

    assert response.status_code == 404


def test_complete_and_uncomplete_item_roundtrip(client, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)
    item_id = path["items"][0]["id"]
    client.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    complete_response = client.post(f"/api/v1/learning-paths/{path['id']}/items/{item_id}/complete")
    assert complete_response.status_code == 204
    detail = client.get(f"/api/v1/learning-paths/{path['id']}").json()
    assert detail["items"][0]["completed"] is True

    uncomplete_response = client.delete(f"/api/v1/learning-paths/{path['id']}/items/{item_id}/complete")
    assert uncomplete_response.status_code == 204
    detail = client.get(f"/api/v1/learning-paths/{path['id']}").json()
    assert detail["items"][0]["completed"] is False


def test_completing_all_items_marks_path_as_completed_in_enrolled_list(client, admin_client):
    path = _create_path_with_items(admin_client, item_count=2)
    client.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    for item in path["items"]:
        client.post(f"/api/v1/learning-paths/{path['id']}/items/{item['id']}/complete")

    enrolled = client.get("/api/v1/learning-paths/enrolled").json()
    assert enrolled[0]["progress_percent"] == 100.0
    assert enrolled[0]["is_completed"] is True


def test_complete_item_is_scoped_to_current_user(client_factory, admin_client):
    path = _create_path_with_items(admin_client, item_count=1)
    item_id = path["items"][0]["id"]
    client_a, _ = client_factory()
    client_b, _ = client_factory()
    client_a.post(f"/api/v1/learning-paths/{path['id']}/enroll")
    client_b.post(f"/api/v1/learning-paths/{path['id']}/enroll")

    client_a.post(f"/api/v1/learning-paths/{path['id']}/items/{item_id}/complete")

    detail_for_b = client_b.get(f"/api/v1/learning-paths/{path['id']}").json()
    assert detail_for_b["items"][0]["completed"] is False
