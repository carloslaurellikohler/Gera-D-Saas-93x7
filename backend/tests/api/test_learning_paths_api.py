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
            user_id=user_id,
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
