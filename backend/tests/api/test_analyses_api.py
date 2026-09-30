from __future__ import annotations


def _create_analysis(client, *, participant_name="João Silva", objective="Onboarding", **extra):
    data = {"participant_name": participant_name, "objective": objective, **extra}
    files = {"file": ("transcricao.txt", b"CS: Oi\nPB: Oi", "text/plain")}
    return client.post("/api/v1/analyses", data=data, files=files)


def test_create_analysis_happy_path(client):
    response = _create_analysis(client, duration_minutes="45")

    assert response.status_code == 201
    body = response.json()
    assert body["participant_name"] == "João Silva"
    assert body["objective"] == "Onboarding"
    assert body["status"] == "UPLOADED"
    assert body["input_type"] == "txt"
    assert body["duration_seconds"] == 45 * 60


def test_create_analysis_rejects_unsupported_extension(client):
    data = {"participant_name": "Maria", "objective": "Feedback"}
    files = {"file": ("audio.wav", b"RIFF....", "audio/wav")}
    response = client.post("/api/v1/analyses", data=data, files=files)

    assert response.status_code == 422


def test_create_analysis_rejects_invalid_objective(client):
    data = {"participant_name": "Maria", "objective": "Objetivo Inexistente"}
    files = {"file": ("t.txt", b"ola", "text/plain")}
    response = client.post("/api/v1/analyses", data=data, files=files)

    assert response.status_code == 422


def test_get_analysis_returns_full_record(client):
    created = _create_analysis(client).json()

    response = client.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_analysis_404_for_unknown_id(client):
    import uuid

    response = client.get(f"/api/v1/analyses/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_status_endpoint(client):
    created = _create_analysis(client).json()

    response = client.get(f"/api/v1/analyses/{created['id']}/status")

    assert response.status_code == 200
    assert response.json()["status"] == "UPLOADED"


def test_list_analyses(client):
    _create_analysis(client, participant_name="Ana")
    _create_analysis(client, participant_name="Bruno")

    response = client.get("/api/v1/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    names = {item["participant_name"] for item in body["items"]}
    assert names == {"Ana", "Bruno"}


def test_list_analyses_filters_by_status(client):
    _create_analysis(client, participant_name="Ana")

    response = client.get("/api/v1/analyses", params={"status": "COMPLETED"})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_transcription_returns_409_before_transcribed(client):
    created = _create_analysis(client).json()

    response = client.get(f"/api/v1/analyses/{created['id']}/transcription")

    assert response.status_code == 409


def test_report_returns_409_before_completed(client):
    created = _create_analysis(client).json()

    response = client.get(f"/api/v1/analyses/{created['id']}/report")

    assert response.status_code == 409


def test_delete_analysis_removes_record_and_file(client, api_service):
    created = _create_analysis(client).json()
    import uuid

    analysis_id = uuid.UUID(created["id"])
    analysis = api_service.repo.get(analysis_id)
    assert api_service.storage.read(analysis.file_path) == b"CS: Oi\nPB: Oi"

    response = client.delete(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 204
    assert api_service.repo.get(analysis_id) is None
    assert not api_service.storage.path(analysis.file_path).exists()


def test_delete_unknown_analysis_404(client):
    import uuid

    response = client.delete(f"/api/v1/analyses/{uuid.uuid4()}")
    assert response.status_code == 404


def test_create_analysis_enqueues_processing_task(client, mocker):
    delay_mock = mocker.patch("app.api.routes.analyses.process_analysis_task.delay")
    response = _create_analysis(client)

    assert response.status_code == 201
    delay_mock.assert_called_once_with(response.json()["id"])


def test_create_analysis_requires_authentication(unauthenticated_client):
    response = _create_analysis(unauthenticated_client)
    assert response.status_code == 401


def test_created_analysis_has_correct_owner(client, api_service):
    import uuid

    created = _create_analysis(client).json()

    analysis = api_service.repo.get(uuid.UUID(created["id"]))
    assert analysis.user_id is not None


def test_list_only_returns_own_for_regular_user(client_factory):
    owner_client, owner = client_factory()
    other_client, _ = client_factory()

    _create_analysis(owner_client, participant_name="Ana")
    _create_analysis(other_client, participant_name="Bruno")

    response = owner_client.get("/api/v1/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participant_name"] == "Ana"


def test_list_returns_all_for_admin(client_factory, admin_client):
    owner_client, _ = client_factory()
    other_client, _ = client_factory()

    _create_analysis(owner_client, participant_name="Ana")
    _create_analysis(other_client, participant_name="Bruno")

    response = admin_client.get("/api/v1/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    names = {item["participant_name"] for item in body["items"]}
    assert names == {"Ana", "Bruno"}


def test_get_404_for_non_owner_non_admin(client_factory):
    owner_client, _ = client_factory()
    other_client, _ = client_factory()

    created = _create_analysis(owner_client).json()

    response = other_client.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 404


def test_admin_can_get_any_analysis(client_factory, admin_client):
    owner_client, _ = client_factory()
    created = _create_analysis(owner_client).json()

    response = admin_client.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_delete_by_owner_allowed(client_factory):
    owner_client, _ = client_factory()
    created = _create_analysis(owner_client).json()

    response = owner_client.delete(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 204


def test_delete_by_non_owner_non_admin_returns_404(client_factory):
    owner_client, _ = client_factory()
    other_client, _ = client_factory()
    created = _create_analysis(owner_client).json()

    response = other_client.delete(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 404


def test_delete_by_admin_allowed(client_factory, admin_client):
    owner_client, _ = client_factory()
    created = _create_analysis(owner_client).json()

    response = admin_client.delete(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 204
