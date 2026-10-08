"""FinAI — captura e custeio do consumo de IA.

Pacote próprio, e não dentro de `engine_integration/`, de propósito: dos quatro pontos de
consumo, dois (AssistantService e scripts/ingest_methodology.py) não têm nada a ver com
`gera_d_engine` e rodam no processo da API. Pôr a captura em `engine_integration/` obrigaria
o assistente a importar de lá, embaralhando a camada que o CLAUDE.md define como "o único
módulo que importa gera_d_engine". Nenhum arquivo daqui importa a engine.
"""

from app.ai_cost.audio import probe_duration_seconds
from app.ai_cost.constants import WHISPER_MODEL_NAME
from app.ai_cost.recorder import (
    DbUsageSink,
    NullUsageSink,
    UsageSink,
    get_usage_sink,
    track_ai_usage,
)
from app.ai_cost.tokenization import count_tokens, count_tokens_batch
from app.ai_cost.usage import PendingUsage

__all__ = [
    "DbUsageSink",
    "NullUsageSink",
    "PendingUsage",
    "UsageSink",
    "WHISPER_MODEL_NAME",
    "count_tokens",
    "count_tokens_batch",
    "get_usage_sink",
    "probe_duration_seconds",
    "track_ai_usage",
]
