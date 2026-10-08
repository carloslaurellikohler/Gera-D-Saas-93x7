"""Agregações de custo de IA em Postgres real (FinAI). Nunca SQLite — as queries usam
date_trunc, FILTER e cast de enum."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.ai_cost import (
    AiUsageCostStatus,
    AiUsageEvent,
    AiUsageFeature,
    AiUsageOperation,
)
from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.ai_cost_repository import AiCostRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture()
def repo(db_session) -> AiCostRepository:
    return AiCostRepository(db_session)


@pytest.fixture()
def cenario(db_session):
    """Dois colaboradores sob um gestor, duas análises, e eventos cobrindo os três tipos de
    operação, uma retentativa e um evento sem preço."""
    gestor = User(
        name="Gestora Ana",
        email=f"gestora-{uuid.uuid4()}@example.com",
        password_hash="x",
        role=UserRole.GESTOR,
        status=UserStatus.ACTIVE,
    )
    db_session.add(gestor)
    db_session.flush()

    colaborador = User(
        name="Colaborador Bruno",
        email=f"bruno-{uuid.uuid4()}@example.com",
        password_hash="x",
        role=UserRole.COLABORADOR,
        status=UserStatus.ACTIVE,
        manager_id=gestor.id,
    )
    outro = User(
        name="Colaboradora Carla",
        email=f"carla-{uuid.uuid4()}@example.com",
        password_hash="x",
        role=UserRole.COLABORADOR,
        status=UserStatus.ACTIVE,
        manager_id=gestor.id,
    )
    db_session.add_all([colaborador, outro])
    db_session.flush()

    analise_caro = Analysis(
        participant_name="PB Caro",
        objective="Onboarding",
        input_type="mp3",
        status=AnalysisStatus.COMPLETED,
        owner_id=colaborador.id,
        interaction_id=str(uuid.uuid4()),
    )
    analise_barata = Analysis(
        participant_name="PB Barato",
        objective="Feedback",
        input_type="docx",
        status=AnalysisStatus.COMPLETED,
        owner_id=outro.id,
        interaction_id=str(uuid.uuid4()),
    )
    db_session.add_all([analise_caro, analise_barata])
    db_session.flush()

    agora = _utcnow()
    eventos = [
        # Análise caro: transcrição + 2 chats, sendo 1 numa retentativa.
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.TRANSCRIPTION,
            stage="TRANSCRIPTION",
            model="whisper-1",
            user_id=colaborador.id,
            analysis_id=analise_caro.id,
            audio_seconds=Decimal("600"),
            cost_usd=Decimal("0.06"),
            cost_status=AiUsageCostStatus.PRICED,
        ),
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="FACT_EXTRACTION",
            model="gpt-6-sol",
            user_id=colaborador.id,
            analysis_id=analise_caro.id,
            input_tokens=10_000,
            output_tokens=2_000,
            cached_input_tokens=1_000,
            reasoning_tokens=500,
            cost_usd=Decimal("0.40"),
            cost_status=AiUsageCostStatus.PRICED,
        ),
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="TRAINING",
            model="gpt-6-sol",
            user_id=colaborador.id,
            analysis_id=analise_caro.id,
            attempt=1,  # retentativa
            input_tokens=20_000,
            output_tokens=3_000,
            cost_usd=Decimal("0.50"),
            cost_status=AiUsageCostStatus.PRICED,
        ),
        # Análise barata: 1 chat sem preço cadastrado.
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="DEVELOPMENT",
            model="modelo-sem-preco",
            user_id=outro.id,
            analysis_id=analise_barata.id,
            input_tokens=5_000,
            output_tokens=1_000,
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_PRICE,
        ),
        # Assistente: 1 chat + 1 embedding, sem análise associada.
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ASSISTANT,
            operation=AiUsageOperation.CHAT,
            stage="ASSISTANT_CHAT",
            model="gpt-6-luna",
            user_id=colaborador.id,
            input_tokens=3_000,
            output_tokens=400,
            cost_usd=Decimal("0.02"),
            cost_status=AiUsageCostStatus.PRICED,
        ),
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ASSISTANT,
            operation=AiUsageOperation.EMBEDDING,
            stage="ASSISTANT_QUESTION_EMBEDDING",
            model="text-embedding-3-small",
            user_id=colaborador.id,
            input_tokens=12,
            tokens_estimated=True,
            cost_usd=Decimal("0.00000024"),
            cost_status=AiUsageCostStatus.PRICED,
        ),
        # Chamada que falhou: sem unidades, com error_type.
        AiUsageEvent(
            occurred_at=agora,
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="PB_CONTEXT",
            model="gpt-6-sol",
            user_id=colaborador.id,
            analysis_id=analise_caro.id,
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_UNITS,
            error_type="APITimeoutError",
        ),
        # Fora da janela de 30 dias — não deve entrar em nenhuma agregação.
        AiUsageEvent(
            occurred_at=agora - timedelta(days=120),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            stage="TRAINING",
            model="gpt-6-sol",
            user_id=colaborador.id,
            input_tokens=999_999,
            cost_usd=Decimal("99.00"),
            cost_status=AiUsageCostStatus.PRICED,
        ),
    ]
    db_session.add_all(eventos)
    db_session.commit()

    return {
        "gestor": gestor,
        "colaborador": colaborador,
        "outro": outro,
        "analise_caro": analise_caro,
        "analise_barata": analise_barata,
    }


def _since(days: int = 30) -> datetime:
    return _utcnow() - timedelta(days=days)


def test_kpis_somam_apenas_a_janela_do_periodo(repo, cenario):
    kpis = repo.kpis(since=_since())

    # 0.06 + 0.40 + 0.50 + 0 + 0.02 + 0.00000024 + 0 — o evento de 120 dias atrás fica fora.
    assert kpis.total_usd == Decimal("0.98000024")
    assert kpis.events == 7


def test_kpis_isolam_custo_de_retentativa(repo, cenario):
    """O multiplicador que hoje é invisível: retry do Celery reexecuta o pipeline inteiro."""
    kpis = repo.kpis(since=_since())

    assert kpis.retry_usd == Decimal("0.50")
    assert kpis.retry_events == 1


def test_kpis_contam_eventos_sem_preco_e_sem_unidades(repo, cenario):
    """São os contadores que impedem a tela de apresentar total subestimado como completo."""
    kpis = repo.kpis(since=_since())

    assert kpis.unpriced_events == 1
    assert kpis.no_units_events == 1
    assert kpis.failed_calls == 1


def test_kpis_agregam_tokens_e_audio(repo, cenario):
    kpis = repo.kpis(since=_since())

    assert kpis.input_tokens == 10_000 + 20_000 + 5_000 + 3_000 + 12
    assert kpis.output_tokens == 2_000 + 3_000 + 1_000 + 400
    assert kpis.cached_input_tokens == 1_000
    assert kpis.reasoning_tokens == 500
    assert kpis.audio_seconds == Decimal("600.000")


def test_kpis_contam_analises_e_mensagens_do_assistente(repo, cenario):
    kpis = repo.kpis(since=_since())

    assert kpis.analyses_with_cost == 2
    assert kpis.assistant_messages == 1


def test_breakdown_por_feature(repo, cenario):
    linhas = {row.key: row.total_usd for row in repo.breakdown_by(dimension="feature", since=_since())}

    assert linhas["ANALYSIS"] == Decimal("0.96")
    assert linhas["ASSISTANT"] == Decimal("0.02000024")


def test_breakdown_por_operacao(repo, cenario):
    linhas = {row.key: row.total_usd for row in repo.breakdown_by(dimension="operation", since=_since())}

    assert linhas["TRANSCRIPTION"] == Decimal("0.06")
    assert linhas["CHAT"] == Decimal("0.92")
    assert linhas["EMBEDDING"] == Decimal("0.00000024")


def test_breakdown_por_etapa_e_por_modelo(repo, cenario):
    etapas = {row.key: row.total_usd for row in repo.breakdown_by(dimension="stage", since=_since())}
    modelos = {row.key: row.total_usd for row in repo.breakdown_by(dimension="model", since=_since())}

    assert etapas["TRAINING"] == Decimal("0.50")
    assert etapas["TRANSCRIPTION"] == Decimal("0.06")
    assert modelos["gpt-6-sol"] == Decimal("0.90")
    assert modelos["modelo-sem-preco"] == Decimal("0")


def test_breakdown_vem_ordenado_do_mais_caro(repo, cenario):
    linhas = repo.breakdown_by(dimension="operation", since=_since())

    assert [row.key for row in linhas][0] == "CHAT"


def test_trend_agrupa_por_dia_e_por_semana(repo, cenario):
    diario = repo.trend(since=_since(), bucket="day")
    semanal = repo.trend(since=_since(), bucket="week")

    assert len(diario) == 1
    assert len(semanal) == 1
    assert diario[0].total_usd == Decimal("0.98000024")
    assert diario[0].events == 7


def test_trend_por_feature_separa_as_series(repo, cenario):
    linhas = repo.trend_by_feature(since=_since(), bucket="day")

    por_feature = {row.feature: row.total_usd for row in linhas}
    assert por_feature["ANALYSIS"] == Decimal("0.96")
    assert por_feature["ASSISTANT"] == Decimal("0.02000024")


def test_top_users_traz_gestor_e_ordena_por_custo(repo, cenario):
    linhas = repo.top_users(since=_since())

    primeiro = linhas[0]
    assert primeiro.name == "Colaborador Bruno"
    assert primeiro.role == "COLABORADOR"
    assert primeiro.manager_name == "Gestora Ana"
    assert primeiro.total_usd == Decimal("0.98000024")
    assert primeiro.analyses == 1
    assert linhas[1].name == "Colaboradora Carla"


def test_top_analyses_ordena_por_custo_e_traz_dono_e_tentativas(repo, cenario):
    linhas = repo.top_analyses(since=_since())

    primeiro = linhas[0]
    assert primeiro.analysis_id == cenario["analise_caro"].id
    assert primeiro.participant_name == "PB Caro"
    assert primeiro.owner_name == "Colaborador Bruno"
    assert primeiro.input_type == "mp3"
    assert primeiro.attempts == 1
    assert primeiro.total_usd == Decimal("0.96")


def test_spend_between_respeita_intervalo_semiaberto(repo, cenario):
    hoje = _utcnow()
    inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)

    gasto = repo.spend_between(start=inicio, end=inicio + timedelta(days=1))

    assert gasto == Decimal("0.98000024")


def test_first_event_at_marca_o_inicio_da_contabilizacao(repo, cenario):
    """A tela declara essa data porque não há backfill."""
    primeiro = repo.first_event_at()

    assert primeiro is not None
    assert primeiro < _utcnow() - timedelta(days=100)


def test_list_events_pagina_e_devolve_total_real(repo, cenario):
    pagina, total = repo.list_events(since=_since(), offset=0, limit=3)

    assert len(pagina) == 3
    # O total é o COUNT de verdade, não len(itens) — numa tela financeira isso é o ponto.
    assert total == 7


def test_list_events_filtra_por_feature_e_usuario(repo, cenario):
    _, total_assistente = repo.list_events(since=_since(), feature="ASSISTANT")
    _, total_carla = repo.list_events(since=_since(), user_id=cenario["outro"].id)

    assert total_assistente == 2
    assert total_carla == 1


def test_list_events_traz_nome_do_usuario_e_status(repo, cenario):
    pagina, _ = repo.list_events(since=_since(), feature="ASSISTANT", operation="EMBEDDING")

    linha = pagina[0]
    assert linha.user_name == "Colaborador Bruno"
    assert linha.cost_status == "PRICED"
    assert linha.tokens_estimated is True


def test_distinct_models_alimenta_o_filtro_da_tela(repo, cenario):
    modelos = repo.distinct_models()

    assert "gpt-6-sol" in modelos
    assert "text-embedding-3-small" in modelos


def test_custo_sobrevive_a_exclusao_do_usuario(repo, cenario, db_session):
    """SET NULL, não CASCADE: o gasto aconteceu de fato e precisa continuar no total do
    período mesmo que o usuário seja removido. Só a atribuição degrada."""
    total_antes = repo.kpis(since=_since()).total_usd

    db_session.delete(cenario["colaborador"])
    db_session.commit()
    db_session.expire_all()

    assert repo.kpis(since=_since()).total_usd == total_antes
    sem_atribuicao = [row for row in repo.top_users(since=_since()) if row.user_id is None]
    assert sem_atribuicao, "eventos do usuario removido deveriam aparecer sem atribuicao"


def test_custo_sobrevive_a_exclusao_da_analise(repo, cenario, db_session):
    """Mesmo racional: com CASCADE, apagar uma análise mudaria o total do mês
    retroativamente."""
    total_antes = repo.kpis(since=_since()).total_usd

    db_session.delete(cenario["analise_caro"])
    db_session.commit()
    db_session.expire_all()

    assert repo.kpis(since=_since()).total_usd == total_antes


def test_importar_so_o_modelo_de_custo_resolve_as_fks():
    """Regressão: ai_usage_events tem FK para analyses e users. Se este módulo for o único
    importado — como acontece em scripts/ingest_methodology.py, que não conhece análise nem
    usuário — o flush quebrava com NoReferencedTableError, e a contabilização ficava
    silenciosamente desligada (o invariante engole a exceção e só loga).

    Roda em subprocesso porque conftest.py já importa todos os modelos no processo de teste,
    o que mascararia o problema.
    """
    import subprocess
    import sys

    script = (
        "from app.models.ai_cost import AiUsageEvent\n"
        "from app.db.base import Base\n"
        "from sqlalchemy.schema import CreateTable\n"
        "from sqlalchemy.dialects import postgresql\n"
        # Compilar o DDL força a resolução de todas as FKs declaradas.
        "print(CreateTable(Base.metadata.tables['ai_usage_events'])"
        ".compile(dialect=postgresql.dialect()))\n"
        "assert 'analyses' in Base.metadata.tables\n"
        "assert 'users' in Base.metadata.tables\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "REFERENCES analyses" in result.stdout
    assert "REFERENCES users" in result.stdout


def test_breakdown_distingue_modelo_sem_preco_de_modelo_barato(repo, cenario):
    """Com US$ 0 nos dois casos, só a contagem de não precificados separa 'custou pouco'
    de 'não sei quanto custou'."""
    modelos = {row.key: row for row in repo.breakdown_by(dimension="model", since=_since())}

    assert modelos["modelo-sem-preco"].unpriced_events == 1
    assert modelos["gpt-6-sol"].unpriced_events == 0


def test_unpriced_models_lista_o_nome_exato_gravado_nos_eventos(repo, cenario):
    """É esta lista, e não a variável de ambiente, que diz o que cadastrar: para chat,
    gravamos o nome que a API reporta, que pode ser um snapshot datado."""
    linhas = repo.unpriced_models()

    assert [(row.model, row.operation, row.events) for row in linhas] == [
        ("modelo-sem-preco", "CHAT", 1)
    ]
    assert linhas[0].first_seen is not None
    assert linhas[0].last_seen is not None


def test_unpriced_models_ignora_periodo(repo, cenario, db_session):
    """Informação de configuração, não de análise: um modelo usado há meses continua
    precisando de preço para o histórico daquele mês fechar certo."""
    db_session.add(
        AiUsageEvent(
            occurred_at=_utcnow() - timedelta(days=200),
            feature=AiUsageFeature.ANALYSIS,
            operation=AiUsageOperation.CHAT,
            model="modelo-antigo-sem-preco",
            cost_usd=Decimal("0"),
            cost_status=AiUsageCostStatus.NO_PRICE,
        )
    )
    db_session.commit()

    modelos = {row.model for row in repo.unpriced_models()}

    assert "modelo-antigo-sem-preco" in modelos


def test_unpriced_models_vazio_quando_tudo_tem_preco(repo, db_session):
    assert repo.unpriced_models() == []
