from __future__ import annotations

from datetime import datetime, timezone

from app.api.deps import get_analysis_service
from app.main import app
from app.models.analysis import Analysis, AnalysisStatus
from app.models.methodology import Calibrator, FarolColor, Methodology, MethodologyStatus
from app.models.user import UserRole
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.methodology_repository import MethodologyRepository


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


def test_list_analyses_includes_owner_name_and_duration(client_factory):
    owner_client, owner = client_factory()
    _create_analysis(owner_client, participant_name="Ana", duration_minutes="30")

    response = owner_client.get("/api/v1/analyses")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["owner_id"] == str(owner.id)
    assert item["owner_name"] == owner.name
    assert item["duration_seconds"] == 30 * 60
    # Análise recém-criada ainda não chegou a COMPLETED — nota/farol não existem.
    assert item["overall_score"] is None
    assert item["overall_farol_level"] is None


def test_list_analyses_includes_score_and_farol_when_completed(client_factory, db_session):
    owner_client, owner = client_factory()
    db_session.add(
        Methodology(
            calibration_version="v1",
            methodology_name="93x7®",
            project="Projeto Teste",
            status=MethodologyStatus.PUBLISHED,
            content={"objective": "Avaliar."},
            calibrators=[
                Calibrator(
                    key="excelente", label="Excelente desempenho", color=FarolColor.VERDE,
                    min=8.0, max=10.0, order_index=0,
                ),
            ],
        )
    )
    db_session.commit()
    AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id="interaction-list-completed",
            owner_id=owner.id,
            status=AnalysisStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            analysis_result={"overall_score": 8.5, "overall_band_label": "Excelente desempenho"},
        )
    )

    response = owner_client.get("/api/v1/analyses")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["overall_score"] == 8.5
    assert item["overall_farol_level"] == "excelente"


def test_list_analyses_total_reflects_full_count_not_just_page(client_factory):
    owner_client, _ = client_factory()
    _create_analysis(owner_client, participant_name="Ana")
    _create_analysis(owner_client, participant_name="Bruno")
    _create_analysis(owner_client, participant_name="Carla")

    response = owner_client.get("/api/v1/analyses", params={"page": 1, "page_size": 1})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["total"] == 3


def test_list_analyses_filters_by_status(client):
    _create_analysis(client, participant_name="Ana")

    response = client.get("/api/v1/analyses", params={"status": "COMPLETED"})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_analyses_filters_by_participant_name(client):
    _create_analysis(client, participant_name="Ana Souza")
    _create_analysis(client, participant_name="Bruno Lima")

    response = client.get("/api/v1/analyses", params={"participant_name": "ana"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participant_name"] == "Ana Souza"


def test_list_analyses_filters_by_date_range(client, api_service):
    import uuid as uuid_module
    from datetime import date as date_cls, datetime as datetime_cls, timezone as timezone_cls

    inside = _create_analysis(client, participant_name="Ana").json()
    outside = _create_analysis(client, participant_name="Bruno").json()
    api_service.repo.update(
        uuid_module.UUID(inside["id"]), created_at=datetime_cls(2026, 1, 15, 12, 0, tzinfo=timezone_cls.utc)
    )
    api_service.repo.update(
        uuid_module.UUID(outside["id"]), created_at=datetime_cls(2026, 2, 1, 12, 0, tzinfo=timezone_cls.utc)
    )

    response = client.get(
        "/api/v1/analyses",
        params={"date_from": date_cls(2026, 1, 1).isoformat(), "date_to": date_cls(2026, 1, 31).isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participant_name"] == "Ana"


def test_gestor_filters_list_by_owner_id_within_team(client_factory):
    gestor_client, gestor = client_factory(role=UserRole.GESTOR)
    colaborador_a_client, colaborador_a = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)
    colaborador_b_client, colaborador_b = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    _create_analysis(gestor_client, owner_id=str(colaborador_a.id), participant_name="Ana")
    _create_analysis(gestor_client, owner_id=str(colaborador_b.id), participant_name="Bruno")

    response = gestor_client.get("/api/v1/analyses", params={"owner_id": str(colaborador_a.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participant_name"] == "Ana"


def test_gestor_filters_list_by_owner_id_outside_team_returns_404(client_factory):
    gestor_client, _ = client_factory(role=UserRole.GESTOR)
    _, outsider = client_factory(role=UserRole.COLABORADOR)

    response = gestor_client.get("/api/v1/analyses", params={"owner_id": str(outsider.id)})

    assert response.status_code == 404


def test_admin_filters_list_by_any_owner_id(client_factory, admin_client):
    owner_client, owner = client_factory()
    other_client, _ = client_factory()

    _create_analysis(owner_client, participant_name="Ana")
    _create_analysis(other_client, participant_name="Bruno")

    response = admin_client.get("/api/v1/analyses", params={"owner_id": str(owner.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participant_name"] == "Ana"


def test_transcription_returns_409_before_transcribed(client):
    created = _create_analysis(client).json()

    response = client.get(f"/api/v1/analyses/{created['id']}/transcription")

    assert response.status_code == 409


def test_report_returns_409_before_completed(client):
    created = _create_analysis(client).json()

    response = client.get(f"/api/v1/analyses/{created['id']}/report")

    assert response.status_code == 409


def test_report_json_includes_overall_farol_level(client_factory, db_session):
    owner_client, owner = client_factory()

    db_session.add(
        Methodology(
            calibration_version="v1",
            methodology_name="93x7®",
            project="Projeto Teste",
            status=MethodologyStatus.PUBLISHED,
            content={"objective": "Avaliar."},
            calibrators=[
                Calibrator(key="excelente", label="Excelente desempenho", color=FarolColor.VERDE, min=8.0, max=10.0, order_index=0),
            ],
        )
    )
    db_session.commit()

    analysis = AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id="interaction-1",
            owner_id=owner.id,
            status=AnalysisStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            analysis_result={"overall_score": 8.5, "overall_band_label": "Excelente desempenho"},
        )
    )

    response = owner_client.get(f"/api/v1/analyses/{analysis.id}/report", params={"format": "json"})

    assert response.status_code == 200
    body = response.json()["analysis_result"]
    assert body["overall_band_label"] == "Excelente desempenho"
    assert body["overall_farol_level"] == "excelente"


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
    assert analysis.owner_id is not None


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


def test_gestor_creates_analysis_for_colaborador_da_equipe(client_factory, api_service):
    import uuid as uuid_module

    gestor_client, gestor = client_factory(role=UserRole.GESTOR)
    _, colaborador = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    response = _create_analysis(gestor_client, owner_id=str(colaborador.id))

    assert response.status_code == 201
    analysis = api_service.repo.get(uuid_module.UUID(response.json()["id"]))
    assert analysis.owner_id == colaborador.id
    assert analysis.created_by_id == gestor.id
    assert analysis.cs_id == str(colaborador.id)
    assert analysis.cs_name == colaborador.name


def test_gestor_criar_analise_sem_owner_id_retorna_422(client_factory):
    gestor_client, _ = client_factory(role=UserRole.GESTOR)

    response = _create_analysis(gestor_client)

    assert response.status_code == 422


def test_gestor_nao_pode_atribuir_analise_fora_da_equipe(client_factory):
    gestor_client, _ = client_factory(role=UserRole.GESTOR)
    _, outsider = client_factory(role=UserRole.COLABORADOR)

    response = _create_analysis(gestor_client, owner_id=str(outsider.id))

    assert response.status_code == 404


def test_colaborador_nao_ve_analise_de_colega_sob_mesmo_gestor(client_factory):
    _, gestor = client_factory(role=UserRole.GESTOR)
    colaborador_a, _ = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)
    colaborador_b, _ = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    created = _create_analysis(colaborador_a, participant_name="Ana").json()

    response = colaborador_b.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 404


def test_gestor_ve_analise_de_colaborador_da_equipe(client_factory):
    gestor_client, gestor = client_factory(role=UserRole.GESTOR)
    colaborador_client, colaborador = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    created = _create_analysis(gestor_client, owner_id=str(colaborador.id), participant_name="Ana").json()

    response = gestor_client.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_gestor_nao_ve_analise_fora_da_equipe(client_factory):
    gestor_client, _ = client_factory(role=UserRole.GESTOR)
    other_client, _ = client_factory(role=UserRole.COLABORADOR)

    created = _create_analysis(other_client, participant_name="Ana").json()

    response = gestor_client.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 404


def test_gestor_list_analyses_retorna_so_a_equipe(client_factory):
    gestor_client, gestor = client_factory(role=UserRole.GESTOR)
    colaborador_client, colaborador = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)
    other_client, _ = client_factory(role=UserRole.COLABORADOR)

    _create_analysis(gestor_client, owner_id=str(colaborador.id), participant_name="Ana")
    _create_analysis(other_client, participant_name="Bruno")

    response = gestor_client.get("/api/v1/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["participant_name"] == "Ana"


def test_create_analysis_returns_429_when_daily_quota_reached(client, api_service_low_quota):
    app.dependency_overrides[get_analysis_service] = lambda: api_service_low_quota

    _create_analysis(client, participant_name="Ana")
    _create_analysis(client, participant_name="Bruno")
    response = _create_analysis(client, participant_name="Carla")

    assert response.status_code == 429


def test_quota_endpoint_returns_used_and_remaining_for_self(client):
    response = client.get("/api/v1/analyses/quota")
    assert response.status_code == 200
    body = response.json()
    assert body["used"] == 0
    assert body["remaining"] == body["limit"]

    _create_analysis(client)

    response = client.get("/api/v1/analyses/quota")
    body = response.json()
    assert body["used"] == 1
    assert body["remaining"] == body["limit"] - 1
    assert body["exempt"] is False


def test_quota_endpoint_scoped_to_owner_for_gestor(client_factory):
    gestor_client, gestor = client_factory(role=UserRole.GESTOR)
    _, colaborador_a = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)
    _, colaborador_b = client_factory(role=UserRole.COLABORADOR, manager_id=gestor.id)

    _create_analysis(gestor_client, owner_id=str(colaborador_a.id))

    response_a = gestor_client.get("/api/v1/analyses/quota", params={"owner_id": str(colaborador_a.id)})
    response_b = gestor_client.get("/api/v1/analyses/quota", params={"owner_id": str(colaborador_b.id)})

    assert response_a.json()["used"] == 1
    assert response_b.json()["used"] == 0


def test_quota_endpoint_404_for_gestor_outside_team(client_factory):
    gestor_client, _ = client_factory(role=UserRole.GESTOR)
    _, outsider = client_factory(role=UserRole.COLABORADOR)

    response = gestor_client.get("/api/v1/analyses/quota", params={"owner_id": str(outsider.id)})

    assert response.status_code == 404


def test_quota_endpoint_404_for_colaborador_querying_others(client_factory):
    colaborador_client, _ = client_factory(role=UserRole.COLABORADOR)
    _, other = client_factory(role=UserRole.COLABORADOR)

    response = colaborador_client.get("/api/v1/analyses/quota", params={"owner_id": str(other.id)})

    assert response.status_code == 404


def test_quota_endpoint_admin_is_exempt(admin_client):
    _create_analysis(admin_client)

    response = admin_client.get("/api/v1/analyses/quota")

    assert response.status_code == 200
    assert response.json()["exempt"] is True


def test_quota_endpoint_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/analyses/quota")
    assert response.status_code == 401
