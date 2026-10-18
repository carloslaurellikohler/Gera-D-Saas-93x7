"""Chamada mínima real à OpenAI para validar um nome de modelo digitado na tela, ANTES de
salvar. Existe porque o campo de modelo em /configuracoes é texto livre: um nome errado só
apareceria depois, com toda análise nova indo para FAILED.

**Deliberadamente NÃO contabilizado no FinAI.** `AiUsageFeature` tem exatamente três valores
(ANALYSIS/ASSISTANT/INGESTION), persistidos como VARCHAR(16) com CHECK; um quarto exigiria DDL
nova, labels no AiCostService e espelho em types/aiCost.ts. E reaproveitar ASSISTANT ou ANALYSIS
distorceria os KPIs que dividem custo por contagem de eventos (avg_usd_per_analysis,
avg_usd_per_assistant_message). Por um teste da ordem de dois tokens, disparado só por ADMIN, a
opção honesta é não rastrear e declarar o porquê aqui.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.services.assistant_llm import is_reasoning_model

# Três freios fecham o vetor de gasto do botão: prompt de um token, teto de saída e nenhuma
# retentativa. O timeout curto também evita prender um worker de uvicorn num modelo lento.
_PROBE_TIMEOUT_SECONDS = 10.0
_PROBE_MAX_TOKENS = 1
_PROBE_PROMPT = "ok"


class ModelProbeError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"O modelo não respondeu: {detail}")


def probe_chat_model(*, model: str, temperature: float | None, api_key: str | None) -> None:
    """Dispara uma chamada real e descarta a resposta. Silencioso em caso de sucesso.

    A mensagem de erro da OpenAI ("The model `x` does not exist") é repassada truncada, de
    propósito: aqui o destinatário é um ADMIN diagnosticando a própria configuração, não o
    colaborador que AnalysisService._SAFE_MESSAGES protege de detalhes de pipeline.
    """
    if not api_key:
        raise ModelProbeError("OPENAI_API_KEY não está configurada neste ambiente.")

    kwargs: dict = {
        "model": model,
        "api_key": api_key,
        "timeout": _PROBE_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    if not is_reasoning_model(model):
        # Modelo de raciocínio rejeita teto de 1 token (o raciocínio consome a cota antes da
        # resposta) e ignora temperature — nos dois casos, melhor nem enviar.
        kwargs["temperature"] = temperature if temperature is not None else 0
        kwargs["max_tokens"] = _PROBE_MAX_TOKENS

    try:
        ChatOpenAI(**kwargs).invoke(_PROBE_PROMPT)
    except Exception as exc:  # NotFoundError, AuthenticationError, APITimeoutError, ...
        raise ModelProbeError(str(exc)[:300]) from exc
