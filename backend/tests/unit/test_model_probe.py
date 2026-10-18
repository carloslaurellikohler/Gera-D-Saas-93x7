from __future__ import annotations

import pytest

from app.services.model_probe import ModelProbeError, probe_chat_model


def test_sucesso_nao_levanta(mocker):
    chat_cls = mocker.patch("app.services.model_probe.ChatOpenAI")

    probe_chat_model(model="gpt-4.1", temperature=0.2, api_key="sk-test")

    chat_cls.return_value.invoke.assert_called_once()


def test_erro_da_openai_vira_erro_de_dominio(mocker):
    chat_cls = mocker.patch("app.services.model_probe.ChatOpenAI")
    chat_cls.return_value.invoke.side_effect = RuntimeError("The model `x` does not exist")

    with pytest.raises(ModelProbeError) as exc:
        probe_chat_model(model="x", temperature=0.2, api_key="sk-test")

    assert "O modelo não respondeu" in str(exc.value)
    assert "does not exist" in str(exc.value)


def test_sem_api_key_nem_instancia_o_client(mocker):
    """Falha antes de qualquer I/O — e com mensagem que diz o que fazer."""
    chat_cls = mocker.patch("app.services.model_probe.ChatOpenAI")

    with pytest.raises(ModelProbeError) as exc:
        probe_chat_model(model="gpt-4.1", temperature=0.2, api_key=None)

    assert "OPENAI_API_KEY" in str(exc.value)
    chat_cls.assert_not_called()


def test_freios_de_gasto_estao_nos_kwargs(mocker):
    """O botão é clicável à vontade: sem retentativa, com timeout curto e teto de 1 token."""
    chat_cls = mocker.patch("app.services.model_probe.ChatOpenAI")

    probe_chat_model(model="gpt-4.1", temperature=0.2, api_key="sk-test")

    kwargs = chat_cls.call_args.kwargs
    assert kwargs["max_retries"] == 0
    assert kwargs["max_tokens"] == 1
    assert kwargs["timeout"] == 10.0


def test_modelo_de_reasoning_omite_temperature_e_max_tokens(mocker):
    """Modelo de raciocínio rejeita teto de 1 token e ignora temperature — mesma regra de
    build_assistant_chat_model, com a lista de prefixos compartilhada."""
    chat_cls = mocker.patch("app.services.model_probe.ChatOpenAI")

    probe_chat_model(model="gpt-6-luna", temperature=0.2, api_key="sk-test")

    kwargs = chat_cls.call_args.kwargs
    assert "temperature" not in kwargs
    assert "max_tokens" not in kwargs


def test_temperatura_nula_cai_em_zero(mocker):
    chat_cls = mocker.patch("app.services.model_probe.ChatOpenAI")

    probe_chat_model(model="gpt-4.1", temperature=None, api_key="sk-test")

    assert chat_cls.call_args.kwargs["temperature"] == 0
