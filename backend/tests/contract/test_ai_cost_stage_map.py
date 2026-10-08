"""Trava do mapa etapa→classe de saída usado pelo FinAI.

`app/ai_cost/stages.py` identifica qual nó da engine disparou cada chamada de chat pelo nome
da classe pydantic passada a `with_structured_output`. Esse módulo não pode importar
`gera_d_engine` (só `engine_integration/` pode), então os nomes são strings literais lá — e é
AQUI, no único lugar do backend autorizado a importar a engine direto, que o acoplamento é
verificado.

Se um nó da engine for renomeado ou acrescentado, este teste falha. Sem ele, a tela passaria
a mostrar "CHAT_NAO_IDENTIFICADO" silenciosamente. Mesmo nesse cenário o custo TOTAL continua
correto — só o detalhamento por etapa degrada.

Não chama a OpenAI: só introspecção.
"""

from __future__ import annotations

from gera_d_engine.pipeline.nodes import normalization
from gera_d_engine.schemas.steps import (
    BehavioralAnalysisOutput,
    ConsequenceAnalysisOutput,
    DevelopmentOutput,
    FactExtractionOutput,
    PbContextOutput,
    TrainingOutput,
)

from app.ai_cost.stages import PIPELINE_STAGE_ORDER, SCHEMA_TO_STAGE, STAGE_LABELS

# Toda classe de saída que algum nó do pipeline passa a with_structured_output.
# `_NormalizationOutput` é privada do próprio nó; as outras seis vivem em schemas/steps.py.
_ENGINE_OUTPUT_SCHEMAS = (
    normalization._NormalizationOutput,
    FactExtractionOutput,
    PbContextOutput,
    BehavioralAnalysisOutput,
    ConsequenceAnalysisOutput,
    DevelopmentOutput,
    TrainingOutput,
)


def test_toda_classe_de_saida_da_engine_tem_etapa_mapeada():
    faltando = [
        schema.__name__ for schema in _ENGINE_OUTPUT_SCHEMAS if schema.__name__ not in SCHEMA_TO_STAGE
    ]
    assert not faltando, (
        f"Classes de saída da engine sem etapa em app/ai_cost/stages.py: {faltando}. "
        "A engine mudou — atualize SCHEMA_TO_STAGE."
    )


def test_mapa_nao_tem_etapa_orfa():
    """O inverso: nome no mapa que a engine não usa mais indica renomeação já ocorrida."""
    nomes_da_engine = {schema.__name__ for schema in _ENGINE_OUTPUT_SCHEMAS}
    orfas = sorted(set(SCHEMA_TO_STAGE) - nomes_da_engine)
    assert not orfas, (
        f"Etapas em SCHEMA_TO_STAGE que nenhum nó da engine produz: {orfas}. "
        "Provavelmente a engine renomeou um schema."
    )


def test_quantidade_de_etapas_de_chat_bate_com_o_pipeline():
    """O pipeline tem 7 nós de LLM (6 sempre + normalização condicional). Se virar 8, o
    gráfico por etapa e a documentação precisam acompanhar."""
    assert len(_ENGINE_OUTPUT_SCHEMAS) == 7
    assert len(SCHEMA_TO_STAGE) == 7


def test_toda_etapa_mapeada_tem_rotulo_e_ordem_de_exibicao():
    for stage in SCHEMA_TO_STAGE.values():
        assert stage in STAGE_LABELS, f"Etapa {stage} sem rótulo em STAGE_LABELS"
        assert stage in PIPELINE_STAGE_ORDER, f"Etapa {stage} fora de PIPELINE_STAGE_ORDER"
