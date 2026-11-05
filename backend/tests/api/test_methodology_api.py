from __future__ import annotations

import uuid

from tests.methodology_factory import valid_payload_dict

_VALID_PAYLOAD = valid_payload_dict()


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


# --- Fase 9 ------------------------------------------------------------------------


def test_publish_with_incomplete_anchors_returns_409(admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()
    payload = valid_payload_dict(calibration_version="sem-ancora")
    payload["anchors"] = [a for a in payload["anchors"] if a["scope_key"] != "conexao"]
    admin_client.put(f"/api/v1/methodology/{created['id']}", json=payload)

    response = admin_client.post(f"/api/v1/methodology/{created['id']}/publish")

    assert response.status_code == 409
    assert "conexao" in response.json()["detail"]


def test_update_draft_with_incomplete_content_returns_422(admin_client):
    """O `content` deixou de ser dict livre: faltar uma chave que a engine lê precisa
    falhar aqui, e não como KeyError no meio de uma análise paga."""
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()
    payload = valid_payload_dict(calibration_version="sem-pilares")
    del payload["content"]["pillars"]

    response = admin_client.put(f"/api/v1/methodology/{created['id']}", json=payload)

    assert response.status_code == 422


def test_prompt_preview_shows_the_compiled_ruler(admin_client):
    created = admin_client.post("/api/v1/methodology/draft", json={}).json()
    admin_client.put(
        f"/api/v1/methodology/{created['id']}", json=valid_payload_dict(calibration_version="previa")
    )

    response = admin_client.get(f"/api/v1/methodology/{created['id']}/prompt-preview")

    assert response.status_code == 200
    body = response.json()
    assert body["calibration_version"] == "previa"
    # o preâmbulo precisa trazer os blocos globais editáveis
    assert "Avaliar." in body["system_preamble"]
    # e o bloco de critérios, a régua compilada a partir das tabelas novas
    assert "sondagem nível 10." in body["criteria_block"]
    assert "nota no máximo 7,9" in body["criteria_block"]
    assert "Profundidade:" in body["criteria_block"]


def test_prompt_preview_is_admin_only(client):
    response = client.get(f"/api/v1/methodology/{uuid.uuid4()}/prompt-preview")
    assert response.status_code == 403
