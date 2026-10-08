"""Captura de consumo de LLM sem tocar em `engine/`.

A engine não pode ser modificada e instancia o próprio `ChatOpenAI` dentro de cada nó
(engine/src/gera_d_engine/pipeline/llm.py), sem nenhum plumbing de callback. A saída é o
hook de ContextVar do LangChain: `register_configure_hook` faz com que qualquer `invoke()`
de chat model que aconteça **dentro** do escopo onde o ContextVar está setado receba o
handler — inclusive os 6-7 invokes que acontecem lá dentro da engine.

================================ ARMADILHA ================================
`register_configure_hook` faz `_configure_hooks.append(...)` numa lista GLOBAL de módulo,
SEM deduplicação. O helper pronto `get_usage_metadata_callback()` do langchain chama
`register_configure_hook` a cada invocação — usá-lo por análise vazaria uma entrada por job
num worker Celery de vida longa, e essa lista é percorrida a cada chamada de LLM.

Por isso o registro aqui é ÚNICO, no import do módulo, e por job só se faz
`set()`/`reset()` do ContextVar (ver recorder.track_ai_usage). Não troque isso por
`get_usage_metadata_callback()`: além do leak, ele agrega por nome de modelo e perde a
granularidade por chamada, que é justamente o que a tela precisa.
===========================================================================
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_core.tracers.context import register_configure_hook

from app.ai_cost.stages import STAGE_UNKNOWN_CHAT, stage_from_invocation_params
from app.ai_cost.usage import PendingUsage
from app.models.ai_cost import AiUsageFeature, AiUsageOperation

log = logging.getLogger(__name__)


class UsageCollector(BaseCallbackHandler):
    """Acumula em memória o consumo das chamadas feitas dentro do seu escopo.

    Só acumula — não calcula custo e não toca banco. Quem persiste é o sink, uma vez, no fim
    do escopo (ver recorder.py), o que mantém o caminho crítico livre de I/O por chamada.
    """

    # O callback manager engole exceções do handler quando isto é False. Contabilizar custo
    # nunca pode derrubar uma análise — e ainda assim cada método abaixo tem seu try/except,
    # porque a garantia é importante demais para depender de um único mecanismo.
    raise_error = False

    def __init__(
        self,
        *,
        feature: AiUsageFeature,
        user_id: uuid.UUID | None = None,
        analysis_id: uuid.UUID | None = None,
        job_run_id: uuid.UUID | None = None,
        attempt: int = 0,
        default_stage: str | None = None,
    ) -> None:
        super().__init__()
        self.feature = feature
        self.user_id = user_id
        self.analysis_id = analysis_id
        self.job_run_id = job_run_id
        self.attempt = attempt
        self.default_stage = default_stage

        self._events: list[PendingUsage] = []
        # run_id → (stage, modelo configurado, instante de início)
        self._in_flight: dict[uuid.UUID, tuple[str | None, str | None, float]] = {}

    # --- API para os consumidores que o LangChain não cobre (Whisper, embeddings) ---

    def add(self, event: PendingUsage) -> None:
        """Registra manualmente uma chamada que não passa por callback do LangChain:
        Whisper (SDK bruto dentro da engine) e embeddings (não são chat models, não emitem
        on_llm_end). Preenche a atribuição a partir do contexto do collector."""
        event.feature = self.feature
        event.user_id = event.user_id or self.user_id
        event.analysis_id = event.analysis_id or self.analysis_id
        event.job_run_id = event.job_run_id or self.job_run_id
        event.attempt = self.attempt
        self._events.append(event)

    def drain(self) -> list[PendingUsage]:
        events, self._events = self._events, []
        return events

    # --- Callbacks do LangChain ---

    def on_chat_model_start(self, serialized: dict[str, Any], messages: Any, **kwargs: Any) -> None:
        try:
            run_id = kwargs.get("run_id")
            params = kwargs.get("invocation_params") or {}
            stage = stage_from_invocation_params(
                params, default=self.default_stage or STAGE_UNKNOWN_CHAT
            )
            if run_id is not None:
                self._in_flight[run_id] = (stage, params.get("model_name"), time.monotonic())
        except Exception:  # noqa: BLE001 — contabilizar custo nunca derruba o caminho crítico
            log.warning("falha ao registrar inicio de chamada de LLM", exc_info=True)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        try:
            stage, configured_model, latency_ms = self._pop_in_flight(kwargs.get("run_id"))
            message = _first_message(response)
            usage = (getattr(message, "usage_metadata", None) or {}) if message else {}
            metadata = (getattr(message, "response_metadata", None) or {}) if message else {}

            self._events.append(
                PendingUsage(
                    feature=self.feature,
                    operation=AiUsageOperation.CHAT,
                    # Modelo real devolvido pela API é melhor que o configurado: é o que de
                    # fato será faturado.
                    model=metadata.get("model_name") or configured_model or "desconhecido",
                    stage=stage or self.default_stage,
                    user_id=self.user_id,
                    analysis_id=self.analysis_id,
                    job_run_id=self.job_run_id,
                    attempt=self.attempt,
                    input_tokens=int(usage.get("input_tokens") or 0),
                    output_tokens=int(usage.get("output_tokens") or 0),
                    cached_input_tokens=int(
                        (usage.get("input_token_details") or {}).get("cache_read") or 0
                    ),
                    reasoning_tokens=int(
                        (usage.get("output_token_details") or {}).get("reasoning") or 0
                    ),
                    latency_ms=latency_ms,
                )
            )
        except Exception:  # noqa: BLE001
            log.warning("falha ao capturar consumo de LLM", exc_info=True)

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Chamada que falhou é registrada com unidades vazias e `error_type` preenchido.

        É o que explica "gastei e não saiu análise": a tentativa fica visível na tela mesmo
        sem valor apurado. A OpenAI pode cobrar parcialmente num erro tardio, e nesse caso
        subcontamos — subcontagem documentada é aceitável, invisível não é.
        """
        try:
            stage, configured_model, latency_ms = self._pop_in_flight(kwargs.get("run_id"))
            self._events.append(
                PendingUsage(
                    feature=self.feature,
                    operation=AiUsageOperation.CHAT,
                    model=configured_model or "desconhecido",
                    stage=stage or self.default_stage,
                    user_id=self.user_id,
                    analysis_id=self.analysis_id,
                    job_run_id=self.job_run_id,
                    attempt=self.attempt,
                    latency_ms=latency_ms,
                    error_type=type(error).__name__,
                )
            )
        except Exception:  # noqa: BLE001
            log.warning("falha ao capturar erro de chamada de LLM", exc_info=True)

    def _pop_in_flight(self, run_id: Any) -> tuple[str | None, str | None, int | None]:
        pending = self._in_flight.pop(run_id, None) if run_id is not None else None
        if pending is None:
            return None, None, None
        stage, configured_model, started = pending
        return stage, configured_model, int((time.monotonic() - started) * 1000)


def _first_message(response: LLMResult) -> Any | None:
    try:
        generation = response.generations[0][0]
    except (IndexError, AttributeError):
        return None
    return generation.message if isinstance(generation, ChatGeneration) else None


# ContextVar + registro ÚNICO no import — ver a seção ARMADILHA na docstring do módulo.
collector_var: ContextVar[UsageCollector | None] = ContextVar(
    "gerad_ai_usage_collector", default=None
)
register_configure_hook(collector_var, True)
