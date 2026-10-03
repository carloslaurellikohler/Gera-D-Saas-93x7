from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.assistant_llm import _is_reasoning_model, build_assistant_chat_model


def test_is_reasoning_model_matches_gpt6_prefix():
    assert _is_reasoning_model("gpt-6-luna") is True
    assert _is_reasoning_model("gpt-6-sol") is True


def test_is_reasoning_model_does_not_match_gpt4():
    assert _is_reasoning_model("gpt-4.1") is False


def test_build_assistant_chat_model_requires_api_key():
    settings = Settings(OPENAI_API_KEY=None)
    with pytest.raises(RuntimeError):
        build_assistant_chat_model(settings)


def test_build_assistant_chat_model_omits_temperature_for_reasoning_model():
    settings = Settings(OPENAI_API_KEY="sk-test", ASSISTANT_CHAT_MODEL="gpt-6-luna")

    model = build_assistant_chat_model(settings)

    assert model.model_name == "gpt-6-luna"
    assert model.temperature is None
