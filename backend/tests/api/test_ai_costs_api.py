"""Rotas do FinAI (custo de IA) — tudo restrito a ADMIN.

Não precisa de override novo em conftest::_overrides: AiCostService só depende de banco
(sem engine, sem storage, sem OpenAI), então o override de get_db já existente basta — mesmo
caso de dashboard e metrics.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.ai_cost import (
    AiUsageCostStatus,
    AiUsageEvent,
    AiUsageFeature,
    AiUsageOperation,
)
from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import UserRole


@pytest.fixture()
def admin_client(client_factory):
    test_client, _ = client_factory(UserRole.ADMIN)
    return test_client


@pytest.fixture()
def seeded_prices(db_session):
    """A migration de seed não roda nos testes (Base.metadata.create_all cria o schema sem
    dados), então os preços conhecidos entram aqui."""
    from app.models.ai_cost import AI_COST_SETTINGS_ID, AiCostSettings, AiModelPrice

    db_session.add_all(
        [
            AiModelPrice(
                model="whisper-1",
                operation=AiUsageOperation.TRANSCRIPTION,
                valid_from=date(2024, 1, 1),
                usd_per_minute=Decimal("0.006"),
            ),
            AiModelPrice(
                model="gpt-6-sol",
                operation=AiUsageOperation.CHAT,
                valid_from=date(2024, 1, 1),
                input_usd_per_mtok=Decimal("2.00"),
                output_usd_per_mtok=Decimal("8.00"),
            ),
            AiCostSettings(id=AI_COST_SETTINGS_ID, warn_threshold_pct=80),
        ]
    )
    db_session.commit()


@pytest.fixture()
def some_events(db_session):
    db_session.add_all(
        [
            AiUsageEvent(
                occurred_at=datetime.now(timezone.utc),
                feature=AiUsageFeature.ANALYSIS,
                operation=AiUsageOperation.CHAT,
                stage="FACT_EXTRACTION",
                model="gpt-6-sol",
                input_tokens=10_000,
                output_tokens=1_000,
                cost_usd=Decimal("0.028"),
                cost_status=AiUsageCostStatus.PRICED,
            ),
            AiUsageEvent(
                occurred_at=datetime.now(timezone.utc),
                feature=AiUsageFeature.ASSISTANT,
                operation=AiUsageOperation.EMBEDDING,
                stage="ASSISTANT_QUESTION_EMBEDDING",
                model="text-embedding-3-small",
                input_tokens=12,
                tokens_estimated=True,
                cost_usd=Decimal("0.00000024"),
                cost_status=AiUsageCostStatus.PRICED,
            ),
        ]
    )
    db_session.commit()


# --- Autorização ---


@pytest.mark.parametrize(
    "path",
    ["/api/v1/ai-costs/summary", "/api/v1/ai-costs/events", "/api/v1/ai-costs/prices", "/api/v1/ai-costs/config"],
)
def test_colaborador_nao_acessa_custo_de_ia(client, path):
    """Custo de operação é informação sensível do negócio — 403, não 404."""
    assert client.get(path).status_code == 403


def test_gestor_nao_acessa_custo_de_ia(client_factory):
    gestor_client, _ = client_factory(UserRole.GESTOR)

    assert gestor_client.get("/api/v1/ai-costs/summary").status_code == 403


def test_sem_autenticacao_e_401(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/ai-costs/summary").status_code == 401


def test_escrita_de_preco_tambem_e_restrita(client):
    resposta = client.post(
        "/api/v1/ai-costs/prices",
        json={
            "model": "gpt-6-sol",
            "operation": "CHAT",
            "valid_from": "2026-01-01",
            "input_usd_per_mtok": 2.0,
            "output_usd_per_mtok": 8.0,
        },
    )

    assert resposta.status_code == 403


# --- Summary ---


def test_summary_sem_dados_responde_200_com_zeros(admin_client):
    """Precedente da Fase 4: sem dados é sempre 200, nunca erro."""
    resposta = admin_client.get("/api/v1/ai-costs/summary?period=30d")

    assert resposta.status_code == 200
    body = resposta.json()
    assert body["kpis"]["total_usd"] == 0
    assert body["kpis"]["events"] == 0
    assert body["by_feature"] == []
    assert body["trend"] == []
    assert body["tracking_started_at"] is None
    assert body["budget"]["status"] == "unset"


def test_summary_agrega_eventos_e_declara_inicio_da_contabilizacao(admin_client, some_events):
    body = admin_client.get("/api/v1/ai-costs/summary?period=30d").json()

    assert body["kpis"]["events"] == 2
    assert body["kpis"]["total_usd"] == pytest.approx(0.02800024)
    assert body["tracking_started_at"] is not None
    features = {item["key"]: item for item in body["by_feature"]}
    assert features["ANALYSIS"]["label"] == "Análises"
    assert features["ASSISTANT"]["total_usd"] == pytest.approx(0.00000024)


def test_summary_traz_rotulo_legivel_por_etapa(admin_client, some_events):
    body = admin_client.get("/api/v1/ai-costs/summary?period=30d").json()

    etapas = {item["key"]: item["label"] for item in body["by_stage"]}
    assert etapas["FACT_EXTRACTION"] == "Extração factual"


def test_summary_escolhe_bucket_por_periodo(admin_client):
    assert admin_client.get("/api/v1/ai-costs/summary?period=7d").json()["trend_bucket"] == "day"
    assert admin_client.get("/api/v1/ai-costs/summary?period=90d").json()["trend_bucket"] == "week"
    assert admin_client.get("/api/v1/ai-costs/summary?period=mtd").json()["trend_bucket"] == "day"


def test_summary_rejeita_periodo_invalido(admin_client):
    assert admin_client.get("/api/v1/ai-costs/summary?period=6m").status_code == 422


# --- Eventos ---


def test_events_pagina_com_total_real(admin_client, some_events):
    body = admin_client.get("/api/v1/ai-costs/events?limit=1").json()

    assert len(body["items"]) == 1
    assert body["total"] == 2  # COUNT de verdade, não len(items)
    assert body["limit"] == 1


def test_events_filtra_por_feature(admin_client, some_events):
    body = admin_client.get("/api/v1/ai-costs/events?feature=ASSISTANT").json()

    assert body["total"] == 1
    assert body["items"][0]["operation"] == "EMBEDDING"
    assert body["items"][0]["tokens_estimated"] is True
    assert body["items"][0]["stage_label"] == "Assistente — embedding da pergunta"


def test_events_lista_modelos_para_o_filtro(admin_client, some_events):
    body = admin_client.get("/api/v1/ai-costs/events").json()

    assert set(body["models"]) == {"gpt-6-sol", "text-embedding-3-small"}


def test_events_trazem_participante_e_filtram_por_analise(admin_client, db_session):
    """O gap reportado: a tela de Chamadas precisa dizer a qual participante avaliado uma
    chamada pertence, e permitir filtrar por análise."""
    analise = Analysis(
        participant_name="PB da Chamada",
        objective="Onboarding",
        input_type="mp3",
        status=AnalysisStatus.COMPLETED,
        interaction_id=str(uuid.uuid4()),
    )
    db_session.add(analise)
    db_session.flush()
    db_session.add(
        AiUsageEvent(
            occurred_at=datetime.now(timezone.utc),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="TRAINING",
            model="gpt-6-sol",
            analysis_id=analise.id,
            input_tokens=100,
            output_tokens=10,
            cost_usd=Decimal("0.01"),
            cost_status=AiUsageCostStatus.PRICED,
        )
    )
    db_session.commit()

    sem_filtro = admin_client.get("/api/v1/ai-costs/events").json()
    assert any(item["participant_name"] == "PB da Chamada" for item in sem_filtro["items"])

    filtrado = admin_client.get(f"/api/v1/ai-costs/events?analysis_id={analise.id}").json()
    assert filtrado["total"] == 1
    assert filtrado["items"][0]["participant_name"] == "PB da Chamada"
    assert filtrado["items"][0]["analysis_id"] == str(analise.id)


# --- Preços ---


def test_lista_precos_marca_vigencia_corrente(admin_client, seeded_prices):
    precos = admin_client.get("/api/v1/ai-costs/prices").json()

    assert len(precos) == 2
    assert all(p["is_current"] for p in precos)


def test_cria_preco_de_chat(admin_client):
    resposta = admin_client.post(
        "/api/v1/ai-costs/prices",
        json={
            "model": "gpt-6-sol",
            "operation": "CHAT",
            "valid_from": "2026-10-01",
            "input_usd_per_mtok": 2.5,
            "cached_input_usd_per_mtok": 0.25,
            "output_usd_per_mtok": 10.0,
            "notes": "Preco conferido na pagina da OpenAI",
        },
    )

    assert resposta.status_code == 201
    body = resposta.json()
    assert body["input_usd_per_mtok"] == 2.5
    # Preço cadastrado pelo ADMIN é preço confirmado.
    assert body["is_placeholder"] is False


def test_preco_de_chat_sem_output_e_recusado(admin_client):
    """Sem preço de saída as chamadas ficariam NO_PRICE e o total apareceria subestimado."""
    resposta = admin_client.post(
        "/api/v1/ai-costs/prices",
        json={
            "model": "gpt-6-sol",
            "operation": "CHAT",
            "valid_from": "2026-10-01",
            "input_usd_per_mtok": 2.5,
        },
    )

    assert resposta.status_code == 422
    assert "saída" in resposta.json()["detail"]


def test_preco_de_transcricao_exige_preco_por_minuto(admin_client):
    resposta = admin_client.post(
        "/api/v1/ai-costs/prices",
        json={
            "model": "whisper-1",
            "operation": "TRANSCRIPTION",
            "valid_from": "2026-10-01",
            "input_usd_per_mtok": 1.0,
        },
    )

    assert resposta.status_code == 422
    assert "minuto" in resposta.json()["detail"]


def test_vigencia_duplicada_responde_409(admin_client):
    payload = {
        "model": "gpt-6-sol",
        "operation": "CHAT",
        "valid_from": "2026-10-01",
        "input_usd_per_mtok": 2.5,
        "output_usd_per_mtok": 10.0,
    }
    assert admin_client.post("/api/v1/ai-costs/prices", json=payload).status_code == 201

    repetido = admin_client.post("/api/v1/ai-costs/prices", json=payload)

    assert repetido.status_code == 409


def test_editar_preco_inexistente_responde_404(admin_client):
    resposta = admin_client.put(
        f"/api/v1/ai-costs/prices/{uuid.uuid4()}",
        json={
            "model": "x",
            "operation": "CHAT",
            "valid_from": "2026-10-01",
            "input_usd_per_mtok": 1.0,
            "output_usd_per_mtok": 2.0,
        },
    )

    assert resposta.status_code == 404


def test_recalculo_reprecifica_eventos_que_estavam_sem_preco(admin_client, db_session):
    """Snapshot congelado tem uma válvula de escape explícita: cadastrar o preço não
    reescreve o passado sozinho, mas /recalculate reescreve quando o ADMIN pede."""
    db_session.add(
        AiUsageEvent(
            occurred_at=datetime.now(timezone.utc),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="TRAINING",
            model="gpt-6-sol",
            input_tokens=1_000_000,
            output_tokens=0,
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_PRICE,
        )
    )
    db_session.commit()

    criado = admin_client.post(
        "/api/v1/ai-costs/prices",
        json={
            "model": "gpt-6-sol",
            "operation": "CHAT",
            "valid_from": "2024-01-01",
            "input_usd_per_mtok": 2.0,
            "output_usd_per_mtok": 8.0,
        },
    ).json()

    # Antes do recálculo, o evento continua com custo zero.
    assert admin_client.get("/api/v1/ai-costs/summary").json()["kpis"]["total_usd"] == 0

    recalculo = admin_client.post(f"/api/v1/ai-costs/prices/{criado['id']}/recalculate")

    assert recalculo.status_code == 200
    assert recalculo.json()["updated"] == 1
    assert admin_client.get("/api/v1/ai-costs/summary").json()["kpis"]["total_usd"] == pytest.approx(2.0)


# --- Configuração e orçamento ---


def test_config_tem_defaults_quando_nada_foi_configurado(admin_client):
    body = admin_client.get("/api/v1/ai-costs/config").json()

    assert body["warn_threshold_pct"] == 80
    assert body["usd_to_brl_rate"] is None
    assert body["current_month_budget_usd"] is None


def test_define_orcamento_e_taxa_de_cambio(admin_client):
    resposta = admin_client.put(
        "/api/v1/ai-costs/config",
        json={"warn_threshold_pct": 70, "usd_to_brl_rate": 5.42, "monthly_budget_usd": 500.0},
    )

    assert resposta.status_code == 200
    body = resposta.json()
    assert body["warn_threshold_pct"] == 70
    assert body["usd_to_brl_rate"] == 5.42
    assert body["usd_to_brl_rate_updated_at"] is not None
    assert body["current_month_budget_usd"] == 500.0


def test_orcamento_aparece_no_summary_com_status(admin_client, some_events):
    admin_client.put(
        "/api/v1/ai-costs/config",
        json={"warn_threshold_pct": 80, "monthly_budget_usd": 0.02},
    )

    budget = admin_client.get("/api/v1/ai-costs/summary?period=mtd").json()["budget"]

    # Gasto do mês (0.028) acima da meta (0.02).
    assert budget["amount_usd"] == 0.02
    assert budget["status"] == "over"
    assert budget["pct"] > 100


def test_orcamento_em_alerta_quando_cruza_o_limiar(admin_client, some_events):
    admin_client.put(
        "/api/v1/ai-costs/config",
        json={"warn_threshold_pct": 50, "monthly_budget_usd": 0.05},
    )

    budget = admin_client.get("/api/v1/ai-costs/summary?period=mtd").json()["budget"]

    assert budget["status"] == "warn"


def test_remover_orcamento_volta_para_unset(admin_client):
    admin_client.put(
        "/api/v1/ai-costs/config", json={"warn_threshold_pct": 80, "monthly_budget_usd": 100.0}
    )

    admin_client.put("/api/v1/ai-costs/config", json={"warn_threshold_pct": 80})

    assert admin_client.get("/api/v1/ai-costs/config").json()["current_month_budget_usd"] is None
    assert admin_client.get("/api/v1/ai-costs/summary").json()["budget"]["status"] == "unset"


def test_limiar_de_alerta_fora_da_faixa_e_recusado(admin_client):
    assert (
        admin_client.put("/api/v1/ai-costs/config", json={"warn_threshold_pct": 0}).status_code
        == 422
    )


# --- Modelos sem preço (fecha o laço entre o que roda e o que está cadastrado) ---


def test_unpriced_models_exige_admin(client):
    assert client.get("/api/v1/ai-costs/unpriced-models").status_code == 403


def test_unpriced_models_vazio_quando_nao_ha_chamada_sem_preco(admin_client, some_events):
    assert admin_client.get("/api/v1/ai-costs/unpriced-models").json() == []


def test_unpriced_models_expoe_o_nome_exato_a_cadastrar(admin_client, db_session):
    """O nome gravado vem de response_metadata["model_name"] — a API costuma devolver um
    snapshot datado, diferente do que está no .env. É este nome que precisa ser cadastrado."""
    db_session.add(
        AiUsageEvent(
            occurred_at=datetime.now(timezone.utc),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="TRAINING",
            model="gpt-6-sol-2026-05-01",
            input_tokens=1000,
            output_tokens=100,
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_PRICE,
        )
    )
    db_session.commit()

    body = admin_client.get("/api/v1/ai-costs/unpriced-models").json()

    assert len(body) == 1
    assert body[0]["model"] == "gpt-6-sol-2026-05-01"
    assert body[0]["operation"] == "CHAT"
    assert body[0]["events"] == 1


def test_summary_marca_quais_modelos_estao_sem_preco(admin_client, db_session):
    db_session.add(
        AiUsageEvent(
            occurred_at=datetime.now(timezone.utc),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            model="modelo-desconhecido",
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_PRICE,
        )
    )
    db_session.commit()

    por_modelo = {m["key"]: m for m in admin_client.get("/api/v1/ai-costs/summary").json()["by_model"]}

    assert por_modelo["modelo-desconhecido"]["unpriced_events"] == 1


def test_cadastrar_o_preco_tira_o_modelo_da_lista_de_pendentes(admin_client, db_session):
    """Cadastrar não reprecifica o histórico (snapshot congelado), mas o modelo sai da
    lista de pendências assim que o recálculo é pedido."""
    db_session.add(
        AiUsageEvent(
            occurred_at=datetime.now(timezone.utc),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            model="gpt-6-sol-2026-05-01",
            input_tokens=1_000_000,
            output_tokens=0,
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_PRICE,
        )
    )
    db_session.commit()

    criado = admin_client.post(
        "/api/v1/ai-costs/prices",
        json={
            "model": "gpt-6-sol-2026-05-01",
            "operation": "CHAT",
            "valid_from": "2024-01-01",
            "input_usd_per_mtok": 2.0,
            "output_usd_per_mtok": 8.0,
        },
    ).json()
    admin_client.post(f"/api/v1/ai-costs/prices/{criado['id']}/recalculate")

    assert admin_client.get("/api/v1/ai-costs/unpriced-models").json() == []
