"""Rotas de /settings — configuração operacional editável em runtime.

Não precisa de override novo em conftest::_overrides: RuntimeSettingsService só depende de
banco (sem engine, sem storage, sem OpenAI — o probe é patchado por módulo quando necessário),
então o override de get_db já existente basta. Mesmo caso de dashboard, metrics e ai_cost.
"""

from __future__ import annotations

import pytest

from app.services.model_probe import ModelProbeError

_PAYLOAD = {
    "daily_analysis_limit_per_owner": 2,
    "assistant_daily_message_limit": 5,
    "analysis_model": "gpt-6-sol",
    "analysis_temperature": 0.5,
    "assistant_model": "gpt-4.1",
    "assistant_temperature": 0.9,
}


# --- Autorização: configuração global é 403, não 404 ---


# TestClient.get() não aceita `json`, então o corpo é opcional por caso.
_ROTAS = [
    ("get", "/api/v1/settings", None),
    ("put", "/api/v1/settings", _PAYLOAD),
    ("post", "/api/v1/settings/test-model", {"model_name": "gpt-4.1"}),
]


def _chamar(test_client, method: str, path: str, body: dict | None):
    kwargs = {} if body is None else {"json": body}
    return getattr(test_client, method)(path, **kwargs)


@pytest.mark.parametrize("method,path,body", _ROTAS)
def test_rotas_exigem_autenticacao(unauthenticated_client, method, path, body):
    assert _chamar(unauthenticated_client, method, path, body).status_code == 401


@pytest.mark.parametrize("method,path,body", _ROTAS)
def test_colaborador_nao_acessa_configuracao(client, method, path, body):
    """Configuração global é informação administrativa — 403, e não o 404 do padrão
    dono-ou-ADMIN (que existe para não revelar IDs de outro usuário)."""
    assert _chamar(client, method, path, body).status_code == 403


def test_gestor_nao_acessa_configuracao(gestor_client):
    assert gestor_client.get("/api/v1/settings").status_code == 403


# --- Leitura ---


def test_get_sem_linha_semeada_devolve_defaults_do_ambiente(admin_client):
    """As migrations não rodam nos testes, então não há linha — a tela tem que mostrar o
    fallback em vez de quebrar."""
    response = admin_client.get("/api/v1/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["daily_analysis_limit_per_owner"] == 4
    assert body["assistant_daily_message_limit"] == 30
    assert body["updated_at"] is None
    assert body["updated_by_name"] is None
    assert "gpt-6" in body["reasoning_model_prefixes"]


# --- Escrita ---


def test_put_persiste_e_reflete_no_get(admin_client):
    assert admin_client.put("/api/v1/settings", json=_PAYLOAD).status_code == 200

    body = admin_client.get("/api/v1/settings").json()
    assert body["daily_analysis_limit_per_owner"] == 2
    assert body["analysis_model"] == "gpt-6-sol"
    assert body["assistant_temperature"] == 0.9


def test_put_registra_quem_editou(admin_client):
    body = admin_client.put("/api/v1/settings", json=_PAYLOAD).json()

    assert body["updated_by_name"] == "Usuária Teste"


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("daily_analysis_limit_per_owner", 0),
        ("daily_analysis_limit_per_owner", 101),
        ("assistant_daily_message_limit", 0),
        ("analysis_temperature", 3),
        ("analysis_temperature", -1),
        ("analysis_model", ""),
        ("assistant_model", "x" * 121),
    ],
)
def test_put_rejeita_valor_fora_de_faixa(admin_client, campo, valor):
    response = admin_client.put("/api/v1/settings", json={**_PAYLOAD, campo: valor})

    assert response.status_code == 422


# --- Testar modelo ---


def test_test_model_devolve_ok_quando_o_modelo_responde(admin_client, mocker):
    probe = mocker.patch("app.services.runtime_settings_service.probe_chat_model")

    response = admin_client.post(
        "/api/v1/settings/test-model", json={"model_name": "gpt-4.1", "temperature": 0.2}
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    probe.assert_called_once()


def test_test_model_devolve_400_com_a_mensagem_da_openai(admin_client, mocker):
    mocker.patch(
        "app.services.runtime_settings_service.probe_chat_model",
        side_effect=ModelProbeError("The model `nao-existe` does not exist"),
    )

    response = admin_client.post(
        "/api/v1/settings/test-model", json={"model_name": "nao-existe", "temperature": 0.2}
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_test_model_nao_persiste_nada(admin_client, mocker):
    """O botão valida um nome digitado; salvar é outro passo, explícito."""
    mocker.patch("app.services.runtime_settings_service.probe_chat_model")

    admin_client.post("/api/v1/settings/test-model", json={"model_name": "gpt-6-sol"})

    assert admin_client.get("/api/v1/settings").json()["analysis_model"] == "gpt-6-luna"
