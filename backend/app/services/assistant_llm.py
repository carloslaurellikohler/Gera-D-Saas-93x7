"""Fábricas de modelo de chat/embedding do Assistente de IA (Fase 6) — distintas das da
engine (gera_d_engine.pipeline.llm), que usa um modelo mais caro (OPENAI_MODEL/gpt-6-sol)
para o pipeline pesado de análise. Pequena duplicação intencional da lógica de prefixo de
"reasoning model", já que o backend não pode importar gera_d_engine fora de
engine_integration/."""

from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import Settings

# Modelos de raciocínio (o1/o3/gpt-5/gpt-6 "thinking") não aceitam `temperature` custom —
# mesma lista de prefixos de engine/src/gera_d_engine/pipeline/llm.py.
_REASONING_MODEL_PREFIXES = ("o1", "o3", "o4", "gpt-5", "gpt-6")


def _is_reasoning_model(model: str) -> bool:
    model_lower = model.lower()
    return model_lower.startswith(_REASONING_MODEL_PREFIXES) and "chat" not in model_lower


def build_assistant_chat_model(settings: Settings) -> ChatOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Defina no ambiente ou em backend/.env "
            "(veja backend/.env.example)."
        )
    kwargs: dict = {"model": settings.ASSISTANT_CHAT_MODEL, "api_key": settings.OPENAI_API_KEY}
    if not _is_reasoning_model(settings.ASSISTANT_CHAT_MODEL):
        kwargs["temperature"] = settings.ASSISTANT_CHAT_TEMPERATURE
    return ChatOpenAI(**kwargs)


def build_embedding_model(settings: Settings) -> OpenAIEmbeddings:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Defina no ambiente ou em backend/.env "
            "(veja backend/.env.example)."
        )
    return OpenAIEmbeddings(model=settings.ASSISTANT_EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)
