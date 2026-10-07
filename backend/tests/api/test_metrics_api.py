from __future__ import annotations

from datetime import datetime, timezone

from app.models.analysis import Analysis, AnalysisStatus
from app.repositories.analysis_repository import AnalysisRepository


def _seed_completed(db_session, *, user_id, interaction_id: str, overall_score: float = 8.0):
    analysis_result = {
        "overall_score": overall_score,
        "overall_band_label": "Excelente desempenho",
        "pilar_93_score": {"key": "pilar_93", "label": "Pilar 93", "score": overall_score},
        "pilar_7_score": {"key": "pilar_7", "label": "Pilar 7", "score": overall_score},
        "scores_by_criterion": [
            {"key": "posicionamento", "label": "Posicionamento", "score": overall_score},
        ],
    }
    return AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id=interaction_id,
            owner_id=user_id,
            status=AnalysisStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            analysis_result=analysis_result,
        )
    )


def test_evolution_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/metrics/evolution")
    assert response.status_code == 401


def test_invalid_period_param_rejected(client):
    response = client.get("/api/v1/metrics/evolution", params={"period": "1y"})
    assert response.status_code == 422


def test_regular_user_sees_only_own_evolution(client_factory, db_session):
    owner_client, owner = client_factory()
    _, other = client_factory()

    _seed_completed(db_session, user_id=owner.id, interaction_id="e1")
    _seed_completed(db_session, user_id=other.id, interaction_id="e2")

    response = owner_client.get("/api/v1/metrics/evolution")

    assert response.status_code == 200
    body = response.json()
    assert len(body["trend"]) == 1
    assert body["trend"][0]["count"] == 1


def test_admin_sees_global_evolution(client_factory, admin_client, db_session):
    _, owner = client_factory()
    _, other = client_factory()

    _seed_completed(db_session, user_id=owner.id, interaction_id="e3")
    _seed_completed(db_session, user_id=other.id, interaction_id="e4")

    response = admin_client.get("/api/v1/metrics/evolution")

    assert response.status_code == 200
    body = response.json()
    assert body["trend"][0]["count"] == 2


def test_user_cannot_override_scope_via_query_param(client_factory, db_session):
    owner_client, owner = client_factory()
    other_client, other = client_factory()

    _seed_completed(db_session, user_id=owner.id, interaction_id="e5")

    response = other_client.get(f"/api/v1/metrics/evolution?user_id={owner.id}")

    assert response.status_code == 200
    assert response.json()["trend"] == []


def test_response_without_data_has_six_empty_radar_points(client):
    response = client.get("/api/v1/metrics/evolution")

    assert response.status_code == 200
    body = response.json()
    assert len(body["radar"]) == 6
    assert all(p["score"] is None for p in body["radar"])
    assert body["trend"] == []
