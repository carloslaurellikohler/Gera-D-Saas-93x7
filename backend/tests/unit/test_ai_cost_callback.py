"""Captura de consumo de LLM (FinAI), sem rede e sem banco.

O mecanismo em teste é o hook de ContextVar do LangChain, que é o que permite medir as
chamadas feitas DENTRO de `engine/` sem modificar a engine. Os testes cobrem as três
propriedades que o mecanismo precisa ter: capturar dentro do escopo, NÃO capturar fora dele,
e não vazar registro de hook entre jobs.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.ai_cost.recorder import track_ai_usage
from app.ai_cost.stages import (
    STAGE_FACT_EXTRACTION,
    STAGE_NORMALIZATION,
    STAGE_UNKNOWN_CHAT,
    stage_from_invocation_params,
)
from app.ai_cost.usage import PendingUsage
from app.models.ai_cost import AiUsageFeature, AiUsageOperation


class FakeSink:
    def __init__(self) -> None:
        self.events: list[PendingUsage] = []

    def flush(self, events: list[PendingUsage]) -> None:
        self.events.extend(events)


class ExplodingSink:
    def flush(self, events: list[PendingUsage]) -> None:  # noqa: ARG002
        raise RuntimeError("banco de custo indisponivel")


def _model(*messages: AIMessage) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter(messages))


def _answer(**usage) -> AIMessage:
    metadata = {
        "input_tokens": 100,
        "output_tokens": 40,
        "total_tokens": 140,
    }
    metadata.update(usage)
    return AIMessage(
        content="ok", usage_metadata=metadata, response_metadata={"model_name": "gpt-6-sol"}
    )


def test_captura_chamada_feita_dentro_do_escopo():
    sink = FakeSink()
    analysis_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with track_ai_usage(
        feature=AiUsageFeature.ANALYSIS,
        user_id=user_id,
        analysis_id=analysis_id,
        attempt=2,
        sink=sink,
    ):
        _model(_answer()).invoke("oi")

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.operation is AiUsageOperation.CHAT
    assert event.feature is AiUsageFeature.ANALYSIS
    # Modelo REAL devolvido pela API, não o configurado.
    assert event.model == "gpt-6-sol"
    assert (event.input_tokens, event.output_tokens) == (100, 40)
    assert event.user_id == user_id
    assert event.analysis_id == analysis_id
    assert event.attempt == 2
    assert event.latency_ms is not None


def test_extrai_detalhes_de_cache_e_reasoning():
    sink = FakeSink()
    answer = _answer(
        input_token_details={"cache_read": 60},
        output_token_details={"reasoning": 25},
    )

    with track_ai_usage(feature=AiUsageFeature.ASSISTANT, sink=sink):
        _model(answer).invoke("oi")

    event = sink.events[0]
    assert event.cached_input_tokens == 60
    assert event.reasoning_tokens == 25


def test_nao_captura_nada_fora_do_escopo():
    """Prova de que o ContextVar é resetado: sem isso, um worker Celery atribuiria o
    consumo de uma análise à anterior."""
    sink = FakeSink()
    model = _model(_answer(), _answer())

    with track_ai_usage(feature=AiUsageFeature.ANALYSIS, sink=sink):
        model.invoke("dentro")
    model.invoke("fora")

    assert len(sink.events) == 1


def test_varias_chamadas_no_mesmo_escopo_geram_um_evento_cada():
    """Espelha o pipeline da engine, que faz 6-7 invokes dentro de um único run_pipeline."""
    sink = FakeSink()
    model = _model(*[_answer() for _ in range(7)])

    with track_ai_usage(feature=AiUsageFeature.ANALYSIS, sink=sink):
        for _ in range(7):
            model.invoke("etapa")

    assert len(sink.events) == 7


def test_eventos_manuais_herdam_a_atribuicao_do_escopo():
    """Whisper e embeddings não passam por callback — entram via collector.add()."""
    sink = FakeSink()
    user_id = uuid.uuid4()

    with track_ai_usage(
        feature=AiUsageFeature.ANALYSIS, user_id=user_id, attempt=1, sink=sink
    ) as usage:
        usage.add(
            PendingUsage(
                feature=AiUsageFeature.ANALYSIS,
                operation=AiUsageOperation.TRANSCRIPTION,
                model="whisper-1",
                audio_seconds=Decimal("120"),
            )
        )

    event = sink.events[0]
    assert event.operation is AiUsageOperation.TRANSCRIPTION
    assert event.user_id == user_id
    assert event.attempt == 1


def test_flush_acontece_mesmo_quando_o_bloco_levanta():
    """Pipeline que falha no meio já queimou tokens — e é exatamente o número que o dono
    da ferramenta quer ver."""
    sink = FakeSink()

    with pytest.raises(ValueError):
        with track_ai_usage(feature=AiUsageFeature.ANALYSIS, sink=sink):
            _model(_answer()).invoke("oi")
            raise ValueError("pipeline falhou depois da primeira etapa")

    assert len(sink.events) == 1


def test_falha_do_sink_nao_propaga():
    """INVARIANTE da feature: contabilizar custo nunca derruba o caminho crítico."""
    with track_ai_usage(feature=AiUsageFeature.ANALYSIS, sink=ExplodingSink()):
        _model(_answer()).invoke("oi")


def test_registro_de_hook_nao_vaza_entre_jobs():
    """Regressão da armadilha documentada em ai_cost/callback.py.

    `register_configure_hook` faz append numa lista global sem dedup. O helper pronto do
    langchain (`get_usage_metadata_callback`) registra a cada invocação — num worker de vida
    longa isso cresce sem limite e a lista é percorrida a cada chamada de LLM. Usa API
    privada do langchain de propósito: é a única forma de travar essa propriedade.
    """
    from langchain_core.tracers import context as langchain_context

    antes = len(langchain_context._configure_hooks)
    for _ in range(50):
        with track_ai_usage(feature=AiUsageFeature.ANALYSIS, sink=FakeSink()):
            pass

    assert len(langchain_context._configure_hooks) == antes


@pytest.mark.parametrize(
    ("schema_name", "esperado"),
    [
        ("_NormalizationOutput", STAGE_NORMALIZATION),
        ("FactExtractionOutput", STAGE_FACT_EXTRACTION),
    ],
)
def test_etapa_vem_da_classe_pydantic_de_saida(schema_name, esperado):
    """`with_structured_output` coloca a classe de saída em invocation_params
    ["response_format"]; cada nó da engine usa uma classe diferente, o que dá etapa
    determinística por chamada (sem depender da ordem de execução)."""
    schema = type(schema_name, (BaseModel,), {"__annotations__": {}})

    assert stage_from_invocation_params({"response_format": schema}) == esperado


def test_etapa_desconhecida_cai_no_default():
    class EsquemaNovoDaEngine(BaseModel):
        pass

    stage = stage_from_invocation_params(
        {"response_format": EsquemaNovoDaEngine}, default=STAGE_UNKNOWN_CHAT
    )

    assert stage == STAGE_UNKNOWN_CHAT


def test_etapa_tolera_response_format_em_dict():
    """Versões da langchain-openai podem passar JSON schema em vez da classe."""
    params = {"response_format": {"json_schema": {"name": "TrainingOutput"}}}

    assert stage_from_invocation_params(params) == "TRAINING"
