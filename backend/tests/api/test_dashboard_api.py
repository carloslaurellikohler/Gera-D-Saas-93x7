from __future__ import annotations


def _create_analysis(client, *, participant_name="João Silva", objective="Onboarding", **extra):
    data = {"participant_name": participant_name, "objective": objective, **extra}
    files = {"file": ("transcricao.txt", b"CS: Oi\nPB: Oi", "text/plain")}
    return client.post("/api/v1/analyses", data=data, files=files)


def test_stats_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401


def test_regular_user_sees_only_own_aggregates(client_factory):
    owner_client, _ = client_factory()
    other_client, _ = client_factory()

    _create_analysis(owner_client, participant_name="Ana")
    _create_analysis(other_client, participant_name="Bruno")

    response = owner_client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["board"] is None
    total_volume = sum(item["count"] for item in body["volume_by_status"])
    assert total_volume == 1


def test_admin_sees_global_aggregates_and_board(client_factory, admin_client):
    owner_client, _ = client_factory()
    other_client, _ = client_factory()

    _create_analysis(owner_client, participant_name="Ana")
    _create_analysis(other_client, participant_name="Bruno")

    response = admin_client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    body = response.json()
    total_volume = sum(item["count"] for item in body["volume_by_status"])
    assert total_volume == 2
    assert body["board"] is not None


def test_user_cannot_override_scope_via_query_param(client_factory):
    owner_client, owner = client_factory()
    other_client, other = client_factory()

    _create_analysis(owner_client, participant_name="Ana")

    response = other_client.get(f"/api/v1/dashboard/stats?user_id={owner.id}")

    assert response.status_code == 200
    total_volume = sum(item["count"] for item in response.json()["volume_by_status"])
    assert total_volume == 0


def test_period_param_limits_query_window(client):
    response = client.get("/api/v1/dashboard/stats", params={"period": "30d"})
    assert response.status_code == 200
    assert response.json()["period"] == "30d"


def test_invalid_period_param_rejected(client):
    response = client.get("/api/v1/dashboard/stats", params={"period": "1y"})
    assert response.status_code == 422
