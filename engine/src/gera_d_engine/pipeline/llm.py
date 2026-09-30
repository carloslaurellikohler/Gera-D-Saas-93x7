"""Fábrica do modelo de chat usado por todas as etapas de IA do pipeline."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from gera_d_engine.config import Settings


def build_chat_model(settings: Settings, *, temperature: float | None = None) -> ChatOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Defina no ambiente ou em engine/.env "
            "(veja engine/.env.example)."
        )
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=settings.openai_temperature if temperature is None else temperature,
    )
