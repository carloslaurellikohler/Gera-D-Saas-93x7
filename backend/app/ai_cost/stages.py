"""Identificação da etapa que originou cada chamada de chat.

As 6-7 chamadas de um pipeline chegam ao callback sem nada que diga qual nó da engine as
disparou. A pista está em `invocation_params["response_format"]`: `with_structured_output`
coloca ali a própria classe pydantic de saída, e cada nó da engine usa uma classe diferente
(verificado em engine/src/gera_d_engine/pipeline/nodes/*.py). Isso dá uma etapa
**determinística por chamada**, sem depender da ordem de execução.

A alternativa seria contar a ordem das chamadas e mapear por posição — frágil: bastaria a
engine inserir um nó para todo o histórico de rótulos sair trocado, silenciosamente.

Este módulo é só strings: não importa `gera_d_engine` (só `engine_integration/` pode fazer
isso). O acoplamento aos nomes das classes é travado por
tests/contract/test_ai_cost_stage_map.py, que importa a engine de verdade e falha se um nó
for renomeado. Mesmo nesse cenário, só o detalhamento por etapa degrada — o custo total
continua correto.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Etapas do pipeline da engine, na ordem de execução de
# engine/src/gera_d_engine/pipeline/run.py. NORMALIZATION é condicional: só roda quando a
# transcrição não vem diarizada, ou seja, quando a entrada foi áudio/vídeo.
STAGE_NORMALIZATION = "NORMALIZATION"
STAGE_FACT_EXTRACTION = "FACT_EXTRACTION"
STAGE_PB_CONTEXT = "PB_CONTEXT"
STAGE_BEHAVIORAL_ANALYSIS = "BEHAVIORAL_ANALYSIS"
STAGE_CONSEQUENCE_ANALYSIS = "CONSEQUENCE_ANALYSIS"
STAGE_DEVELOPMENT = "DEVELOPMENT"
STAGE_TRAINING = "TRAINING"

# Etapas fora do pipeline.
STAGE_TRANSCRIPTION = "TRANSCRIPTION"
STAGE_ASSISTANT_CHAT = "ASSISTANT_CHAT"
STAGE_ASSISTANT_QUESTION_EMBEDDING = "ASSISTANT_QUESTION_EMBEDDING"
STAGE_CORPUS_EMBEDDING = "CORPUS_EMBEDDING"

# Usado quando a classe de saída não é reconhecida — ver docstring do módulo.
STAGE_UNKNOWN_CHAT = "CHAT_NAO_IDENTIFICADO"

# Nome da classe pydantic passada a with_structured_output → etapa. `_NormalizationOutput`
# é privada da engine (definida dentro do próprio nó), as outras seis vivem em
# gera_d_engine.schemas.steps.
SCHEMA_TO_STAGE: dict[str, str] = {
    "_NormalizationOutput": STAGE_NORMALIZATION,
    "FactExtractionOutput": STAGE_FACT_EXTRACTION,
    "PbContextOutput": STAGE_PB_CONTEXT,
    "BehavioralAnalysisOutput": STAGE_BEHAVIORAL_ANALYSIS,
    "ConsequenceAnalysisOutput": STAGE_CONSEQUENCE_ANALYSIS,
    "DevelopmentOutput": STAGE_DEVELOPMENT,
    "TrainingOutput": STAGE_TRAINING,
}

# Ordem canônica para exibição na tela — espelha run.py, para o gráfico por etapa não mudar
# de ordem entre chamadas.
PIPELINE_STAGE_ORDER: tuple[str, ...] = (
    STAGE_TRANSCRIPTION,
    STAGE_NORMALIZATION,
    STAGE_FACT_EXTRACTION,
    STAGE_PB_CONTEXT,
    STAGE_BEHAVIORAL_ANALYSIS,
    STAGE_CONSEQUENCE_ANALYSIS,
    STAGE_DEVELOPMENT,
    STAGE_TRAINING,
)

STAGE_LABELS: dict[str, str] = {
    STAGE_TRANSCRIPTION: "Transcrição (Whisper)",
    STAGE_NORMALIZATION: "Normalização",
    STAGE_FACT_EXTRACTION: "Extração factual",
    STAGE_PB_CONTEXT: "Contexto do PB",
    STAGE_BEHAVIORAL_ANALYSIS: "Análise comportamental",
    STAGE_CONSEQUENCE_ANALYSIS: "Análise de consequência",
    STAGE_DEVELOPMENT: "Desenvolvimento",
    STAGE_TRAINING: "T&D e avaliação final",
    STAGE_ASSISTANT_CHAT: "Assistente — resposta",
    STAGE_ASSISTANT_QUESTION_EMBEDDING: "Assistente — embedding da pergunta",
    STAGE_CORPUS_EMBEDDING: "Ingestão do corpus",
    STAGE_UNKNOWN_CHAT: "Chat não identificado",
}


def stage_label(stage: str | None) -> str:
    if stage is None:
        return "Sem etapa"
    return STAGE_LABELS.get(stage, stage)


def stage_from_invocation_params(
    invocation_params: Mapping[str, Any] | None, *, default: str | None = None
) -> str | None:
    """Etapa a partir dos parâmetros de invocação do chat model.

    Tolera as várias formas que `response_format` pode assumir entre versões da
    langchain-openai: a classe pydantic (forma atual, confirmada na 1.6.6), ou um dict de
    JSON schema. Também olha `ls_structured_output_format`, que versões mais novas podem
    passar. Não reconhecendo nada, devolve `default`.
    """
    params = invocation_params or {}

    schema_name = _name_from_response_format(params.get("response_format"))
    if schema_name is None:
        schema_name = _name_from_ls_format(params.get("ls_structured_output_format"))

    if schema_name is None:
        return default
    return SCHEMA_TO_STAGE.get(schema_name, default)


def _name_from_response_format(response_format: Any) -> str | None:
    if response_format is None:
        return None
    # Forma atual: a própria classe pydantic.
    if isinstance(response_format, type):
        return response_format.__name__
    if isinstance(response_format, Mapping):
        json_schema = response_format.get("json_schema")
        if isinstance(json_schema, Mapping):
            name = json_schema.get("name") or (json_schema.get("schema") or {}).get("title")
            if name:
                return str(name)
        name = response_format.get("name") or response_format.get("title")
        if name:
            return str(name)
    return None


def _name_from_ls_format(ls_format: Any) -> str | None:
    if not isinstance(ls_format, Mapping):
        return None
    schema = ls_format.get("schema")
    if isinstance(schema, Mapping):
        function = schema.get("function")
        if isinstance(function, Mapping) and function.get("name"):
            return str(function["name"])
        if schema.get("title"):
            return str(schema["title"])
    return None
