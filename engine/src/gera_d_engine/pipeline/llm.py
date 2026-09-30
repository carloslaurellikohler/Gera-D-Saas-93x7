"""Fábrica do modelo de chat usado por todas as etapas de IA do pipeline."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from gera_d_engine.config import Settings

# Modelos de raciocínio (o1/o3/gpt-5/gpt-6 "thinking") não aceitam `temperature` custom —
# a langchain-openai instalada só reconhece isso para os prefixos "o1" e "gpt-5".
_REASONING_MODEL_PREFIXES = ("o1", "o3", "o4", "gpt-5", "gpt-6")


def _is_reasoning_model(model: str) -> bool:
    model_lower = model.lower()
    return model_lower.startswith(_REASONING_MODEL_PREFIXES) and "chat" not in model_lower


def build_chat_model(settings: Settings, *, temperature: float | None = None) -> ChatOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Defina no ambiente ou em engine/.env "
            "(veja engine/.env.example)."
        )
    kwargs: dict = {"model": settings.openai_model, "api_key": settings.openai_api_key}
    if not _is_reasoning_model(settings.openai_model):
        kwargs["temperature"] = settings.openai_temperature if temperature is None else temperature
    return ChatOpenAI(**kwargs)
