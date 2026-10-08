"""Cálculo de custo (FinAI). São funções puras — nenhum teste aqui toca banco ou rede.

Os dois primeiros testes cobrem erros que são fáceis de cometer e invisíveis em produção:
cobrar reasoning tokens em dobro e cobrar input cacheado como input cheio.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.ai_cost.pricing import PriceSnapshot, compute_cost, has_measured_units
from app.ai_cost.usage import PendingUsage
from app.models.ai_cost import AiUsageCostStatus, AiUsageFeature, AiUsageOperation

_PRICE_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")

_CHAT_PRICE = PriceSnapshot(
    price_id=_PRICE_ID,
    input_usd_per_mtok=Decimal("2.00"),
    cached_input_usd_per_mtok=Decimal("0.50"),
    output_usd_per_mtok=Decimal("8.00"),
)


def _chat(**kwargs) -> PendingUsage:
    defaults = dict(
        feature=AiUsageFeature.ANALYSIS,
        operation=AiUsageOperation.CHAT,
        model="gpt-teste",
    )
    defaults.update(kwargs)
    return PendingUsage(**defaults)


def test_chat_cobra_input_output_e_cache_separadamente():
    usage = _chat(input_tokens=1_000_000, output_tokens=1_000_000, cached_input_tokens=400_000)

    cost, status, price_id = compute_cost(usage, _CHAT_PRICE)

    # 600k input cheio a 2.00/Mtok = 1.20; 400k cacheado a 0.50/Mtok = 0.20;
    # 1M output a 8.00/Mtok = 8.00 -> total 9.40
    assert cost == Decimal("9.4000000000")
    assert status is AiUsageCostStatus.PRICED
    assert price_id == _PRICE_ID


def test_reasoning_tokens_nao_sao_cobrados_em_dobro():
    """usage_metadata["output_tokens"] já inclui os reasoning tokens. Se algum dia alguém
    somar `reasoning_tokens` ao custo, este teste quebra."""
    sem_reasoning = _chat(input_tokens=0, output_tokens=1_000_000)
    com_reasoning = _chat(input_tokens=0, output_tokens=1_000_000, reasoning_tokens=800_000)

    assert compute_cost(sem_reasoning, _CHAT_PRICE)[0] == compute_cost(com_reasoning, _CHAT_PRICE)[0]


def test_sem_preco_de_cache_o_token_cacheado_e_cobrado_como_input_cheio():
    """Erra para cima, nunca para baixo — subestimar custo é a falha perigosa nesta tela."""
    price = PriceSnapshot(
        price_id=_PRICE_ID,
        input_usd_per_mtok=Decimal("2.00"),
        cached_input_usd_per_mtok=None,
        output_usd_per_mtok=Decimal("0.00"),
    )
    usage = _chat(input_tokens=1_000_000, cached_input_tokens=1_000_000)

    cost, status, _ = compute_cost(usage, price)

    assert cost == Decimal("2.0000000000")
    assert status is AiUsageCostStatus.PRICED


def test_cached_maior_que_input_nao_gera_input_negativo():
    usage = _chat(input_tokens=1_000, cached_input_tokens=5_000)

    cost, _, _ = compute_cost(usage, _CHAT_PRICE)

    # Todos os 1.000 tokens tratados como cacheados: 1000/1M * 0.50
    assert cost == Decimal("0.0005000000")


def test_embedding_minusculo_nao_arredonda_para_zero():
    """O motivo de cost_usd ser Numeric(18, 10): com escala 6 isto viraria 0.000000."""
    price = PriceSnapshot(price_id=_PRICE_ID, input_usd_per_mtok=Decimal("0.02"))
    usage = PendingUsage(
        feature=AiUsageFeature.ASSISTANT,
        operation=AiUsageOperation.EMBEDDING,
        model="text-embedding-3-small",
        input_tokens=10,
    )

    cost, status, _ = compute_cost(usage, price)

    assert cost == Decimal("0.0000002000")
    assert cost > 0
    assert status is AiUsageCostStatus.PRICED


def test_transcricao_cobra_por_minuto_de_audio():
    price = PriceSnapshot(price_id=_PRICE_ID, usd_per_minute=Decimal("0.006"))
    usage = PendingUsage(
        feature=AiUsageFeature.ANALYSIS,
        operation=AiUsageOperation.TRANSCRIPTION,
        model="whisper-1",
        audio_seconds=Decimal("90"),
    )

    cost, status, _ = compute_cost(usage, price)

    assert cost == Decimal("0.0090000000")  # 1,5 min * 0,006
    assert status is AiUsageCostStatus.PRICED


def test_sem_preco_cadastrado_devolve_no_price_e_custo_zero():
    cost, status, price_id = compute_cost(_chat(input_tokens=1000, output_tokens=500), None)

    assert cost == Decimal("0")
    assert status is AiUsageCostStatus.NO_PRICE
    assert price_id is None


def test_preco_de_chat_incompleto_conta_como_sem_preco():
    """Linha de CHAT sem preço de output não pode render custo parcial passando por PRICED."""
    incompleto = PriceSnapshot(price_id=_PRICE_ID, input_usd_per_mtok=Decimal("2.00"))

    _, status, _ = compute_cost(_chat(input_tokens=1000, output_tokens=500), incompleto)

    assert status is AiUsageCostStatus.NO_PRICE


def test_sem_unidades_medidas_devolve_no_units():
    """Cobre chamada que falhou, resposta sem usage_metadata e ffprobe indisponível."""
    cost, status, _ = compute_cost(_chat(error_type="APITimeoutError"), _CHAT_PRICE)

    assert cost == Decimal("0")
    assert status is AiUsageCostStatus.NO_UNITS


def test_transcricao_sem_duracao_medida_devolve_no_units():
    price = PriceSnapshot(price_id=_PRICE_ID, usd_per_minute=Decimal("0.006"))
    usage = PendingUsage(
        feature=AiUsageFeature.ANALYSIS,
        operation=AiUsageOperation.TRANSCRIPTION,
        model="whisper-1",
        audio_seconds=None,
    )

    assert has_measured_units(usage) is False
    assert compute_cost(usage, price)[1] is AiUsageCostStatus.NO_UNITS


def test_soma_de_muitos_eventos_minusculos_e_exata():
    """Decimal, não float: um milhão de embeddings de 1 token a 0,02/Mtok dá exatamente 0,02."""
    price = PriceSnapshot(price_id=_PRICE_ID, input_usd_per_mtok=Decimal("0.02"))
    usage = PendingUsage(
        feature=AiUsageFeature.ASSISTANT,
        operation=AiUsageOperation.EMBEDDING,
        model="text-embedding-3-small",
        input_tokens=1,
    )

    unitario, _, _ = compute_cost(usage, price)

    assert unitario * 1_000_000 == Decimal("0.02")
