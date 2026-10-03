from __future__ import annotations

import uuid

_VALID_PAYLOAD = {
    "calibration_version": "v2",
    "methodology_name": "93x7®",
    "project": "Projeto Teste",
    "content": {"objective": "Avaliar."},
    "categories": [
        {"key": "posicionamento", "label": "Posicionamento", "description": "d", "order_index": 0, "extra": {}},
        {"key": "conexao", "label": "Conexão", "description": "d", "order_index": 1, "extra": {}},
        {"key": "sondagem", "label": "Sondagem", "description": "d", "order_index": 2, "extra": {}},
        {"key": "direcionamento", "label": "Direcionamento", "description": "d", "order_index": 3, "extra": {}},
        {"key": "encaminhamento", "label": "Encaminhamento", "description": "d", "order_index": 4, "extra": {}},
        {"key": "eficiencia_conducao", "label": "Eficiência", "description": "d", "order_index": 5, "extra": {}},
    ],
    "calibrators": [
        {"key": "excelente", "label": "Excelente", "color": "verde", "min": 8.0, "max": 10.0, "order_index": 0},
        {"key": "atencao", "label": "Atenção", "color": "amarelo", "min": 7.0, "max": 7.9, "order_index": 1},
        {"key": "prioritario", "label": "Prioritário", "color": "laranja", "min": 6.0, "max": 6.9, "order_index": 2},
        {"key": "critico", "label": "Crítico", "color": "vermelho", "min": 0.0, "max": 5.9, "order_index": 3},
    ],
}


def test_list_methodologies_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/methodology")
    assert response.status_code == 401


def test_regular_user_cannot_create_draft(client):
    response = client.post("/api/v1/methodology/draft", json={})
    assert response.status_code == 403


def test_admin_can_create_empty_draft(admin_client):
    response = admin_client.post("/api/v1/methodology/draft", json={})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["categories"] == []


def test_regular_user_can_list_and_read(client, admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()

    list_response = client.get("/api/v1/methodology")
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json())

    detail_response = client.get(f"/api/v1/methodology/{created['id']}")
    assert detail_response.status_code == 200


def test_get_methodology_not_found(client):
    response = client.get(f"/api/v1/methodology/{uuid.uuid4()}")
    assert response.status_code == 404


def test_published_returns_404_when_none_published(client):
    response = client.get("/api/v1/methodology/published")
    assert response.status_code == 404


def test_full_draft_update_publish_flow(admin_client, client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()

    update_response = admin_client.put(f"/api/v1/methodology/{created['id']}", json=_VALID_PAYLOAD)
    assert update_response.status_code == 200
    assert update_response.json()["calibration_version"] == "v2"

    publish_response = admin_client.post(f"/api/v1/methodology/{created['id']}/publish")
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "PUBLISHED"

    published = client.get("/api/v1/methodology/published")
    assert published.status_code == 200
    assert published.json()["id"] == created["id"]


def test_publish_rejects_incomplete_categories(admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()
    payload = {**_VALID_PAYLOAD, "categories": _VALID_PAYLOAD["categories"][:-1]}
    admin_client.put(f"/api/v1/methodology/{created['id']}", json=payload)

    response = admin_client.post(f"/api/v1/methodology/{created['id']}/publish")

    assert response.status_code == 409


def test_update_requires_admin(client, admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()

    response = client.put(f"/api/v1/methodology/{created['id']}", json=_VALID_PAYLOAD)

    assert response.status_code == 403


def test_publishing_archives_previous_version(admin_client):
    first = admin_client.post("/api/v1/methodology/draft", json={}).json()
    admin_client.put(f"/api/v1/methodology/{first['id']}", json=_VALID_PAYLOAD)
    admin_client.post(f"/api/v1/methodology/{first['id']}/publish")

    second = admin_client.post(
        "/api/v1/methodology/draft", json={"from_id": first["id"]}
    ).json()
    second_payload = {**_VALID_PAYLOAD, "calibration_version": "v3"}
    admin_client.put(f"/api/v1/methodology/{second['id']}", json=second_payload)
    admin_client.post(f"/api/v1/methodology/{second['id']}/publish")

    archived = admin_client.get(f"/api/v1/methodology/{first['id']}").json()
    assert archived["status"] == "ARCHIVED"


def test_delete_draft_requires_admin(client, admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()

    response = client.delete(f"/api/v1/methodology/{created['id']}")

    assert response.status_code == 403


def test_admin_can_delete_draft(admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()

    response = admin_client.delete(f"/api/v1/methodology/{created['id']}")

    assert response.status_code == 204
    assert admin_client.get(f"/api/v1/methodology/{created['id']}").status_code == 404


def test_delete_published_methodology_is_rejected(admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()
    admin_client.put(f"/api/v1/methodology/{created['id']}", json=_VALID_PAYLOAD)
    admin_client.post(f"/api/v1/methodology/{created['id']}/publish")

    response = admin_client.delete(f"/api/v1/methodology/{created['id']}")

    assert response.status_code == 409
