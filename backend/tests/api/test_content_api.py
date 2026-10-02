from __future__ import annotations


def test_create_content_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.post("/api/v1/content", data={"title": "T", "kind": "LINK"})
    assert response.status_code == 401


def test_regular_user_cannot_create_content(client):
    response = client.post(
        "/api/v1/content",
        data={"title": "Vídeo", "kind": "LINK", "external_url": "https://example.com"},
    )
    assert response.status_code == 403


def test_admin_can_create_link_content(admin_client):
    response = admin_client.post(
        "/api/v1/content",
        data={"title": "Vídeo-aula", "kind": "LINK", "external_url": "https://example.com/video"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "LINK"
    assert body["external_url"] == "https://example.com/video"
    assert body["file_path"] is None


def test_admin_can_upload_pdf_content(admin_client):
    response = admin_client.post(
        "/api/v1/content",
        data={"title": "Apostila", "kind": "FILE", "criterion_key": "sondagem"},
        files={"file": ("apostila.pdf", b"%PDF-1.4" + b"\x00" * 10, "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "FILE"
    assert body["file_path"] is not None


def test_create_content_rejects_unsupported_extension(admin_client):
    response = admin_client.post(
        "/api/v1/content",
        data={"title": "Vídeo upload", "kind": "FILE"},
        files={"file": ("aula.mp4", b"\x00" * 10, "video/mp4")},
    )
    assert response.status_code == 422


def test_list_content_empty_returns_200(client):
    response = client.get("/api/v1/content")
    assert response.status_code == 200
    assert response.json() == []


def test_get_content_not_found(client):
    import uuid

    response = client.get(f"/api/v1/content/{uuid.uuid4()}")
    assert response.status_code == 404


def test_update_content_requires_admin(client, admin_client):
    created = admin_client.post(
        "/api/v1/content",
        data={"title": "Vídeo", "kind": "LINK", "external_url": "https://example.com"},
    ).json()

    response = client.put(
        f"/api/v1/content/{created['id']}",
        data={"title": "Vídeo atualizado", "external_url": "https://example.com/novo"},
    )
    assert response.status_code == 403


def test_update_content_not_found(admin_client):
    import uuid

    response = admin_client.put(
        f"/api/v1/content/{uuid.uuid4()}",
        data={"title": "Qualquer", "external_url": "https://example.com"},
    )
    assert response.status_code == 404


def test_admin_can_update_content_link_metadata_and_url(admin_client):
    created = admin_client.post(
        "/api/v1/content",
        data={"title": "Vídeo-aula", "kind": "LINK", "external_url": "https://example.com/video"},
    ).json()

    response = admin_client.put(
        f"/api/v1/content/{created['id']}",
        data={
            "title": "Vídeo-aula atualizada",
            "description": "Nova descrição",
            "external_url": "https://example.com/video-novo",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Vídeo-aula atualizada"
    assert body["description"] == "Nova descrição"
    assert body["external_url"] == "https://example.com/video-novo"


def test_update_content_link_without_url_returns_422(admin_client):
    created = admin_client.post(
        "/api/v1/content",
        data={"title": "Vídeo-aula", "kind": "LINK", "external_url": "https://example.com/video"},
    ).json()

    response = admin_client.put(f"/api/v1/content/{created['id']}", data={"title": "Sem URL"})

    assert response.status_code == 422


def test_admin_can_update_content_file_with_new_upload(admin_client):
    created = admin_client.post(
        "/api/v1/content",
        data={"title": "Apostila", "kind": "FILE"},
        files={"file": ("apostila.pdf", b"%PDF-1.4" + b"\x00" * 10, "application/pdf")},
    ).json()

    response = admin_client.put(
        f"/api/v1/content/{created['id']}",
        data={"title": "Apostila v2"},
        files={"file": ("apostila-v2.pdf", b"%PDF-1.4" + b"\x11" * 20, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Apostila v2"
    assert body["file_path"] != created["file_path"]


def test_delete_content_requires_admin(client, admin_client):
    created = admin_client.post(
        "/api/v1/content",
        data={"title": "Removível", "kind": "LINK", "external_url": "https://example.com"},
    ).json()

    response = client.delete(f"/api/v1/content/{created['id']}")
    assert response.status_code == 403


def test_admin_can_delete_unreferenced_content(admin_client):
    created = admin_client.post(
        "/api/v1/content",
        data={"title": "Removível", "kind": "LINK", "external_url": "https://example.com"},
    ).json()

    response = admin_client.delete(f"/api/v1/content/{created['id']}")
    assert response.status_code == 204
    assert admin_client.get(f"/api/v1/content/{created['id']}").status_code == 404


def test_delete_content_blocked_when_referenced_by_learning_path(admin_client):
    content = admin_client.post(
        "/api/v1/content",
        data={"title": "Em uso", "kind": "LINK", "external_url": "https://example.com"},
    ).json()
    admin_client.post(
        "/api/v1/learning-paths",
        json={"title": "Trilha", "items": [{"content_id": content["id"], "order_index": 0}]},
    )

    response = admin_client.delete(f"/api/v1/content/{content['id']}")

    assert response.status_code == 409
