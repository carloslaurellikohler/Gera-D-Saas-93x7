from __future__ import annotations

from datetime import datetime, timezone

from app.models.chat_message import ChatMessage, ChatMessageRole
from app.repositories.chat_message_repository import ChatMessageRepository


def test_get_history_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/assistant/messages")
    assert response.status_code == 401


def test_send_message_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.post("/api/v1/assistant/messages", json={"content": "oi"})
    assert response.status_code == 401


def test_get_history_empty_for_new_user(client):
    response = client.get("/api/v1/assistant/messages")
    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_send_message_returns_assistant_reply(client):
    response = client.post("/api/v1/assistant/messages", json={"content": "O que é o Pilar 7?"})

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "assistant"
    assert body["content"] == "resposta mockada do assistente"


def test_send_message_persists_history(client):
    client.post("/api/v1/assistant/messages", json={"content": "primeira pergunta"})

    history = client.get("/api/v1/assistant/messages").json()["messages"]

    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "primeira pergunta"


def test_send_message_rejects_empty_content(client):
    response = client.post("/api/v1/assistant/messages", json={"content": ""})
    assert response.status_code == 422


def test_history_is_isolated_between_users(client_factory):
    client_a, _ = client_factory()
    client_b, _ = client_factory()

    client_a.post("/api/v1/assistant/messages", json={"content": "pergunta da usuária A"})

    history_a = client_a.get("/api/v1/assistant/messages").json()["messages"]
    history_b = client_b.get("/api/v1/assistant/messages").json()["messages"]

    assert len(history_a) == 2
    assert history_b == []


def test_admin_also_only_sees_own_history(admin_client, client):
    client.post("/api/v1/assistant/messages", json={"content": "pergunta de usuário comum"})

    admin_history = admin_client.get("/api/v1/assistant/messages").json()["messages"]

    assert admin_history == []


def test_send_message_returns_429_when_daily_limit_reached(client, db_session):
    repo = ChatMessageRepository(db_session)
    me = client.get("/api/v1/auth/me").json()
    for i in range(30):
        repo.create(ChatMessage(user_id=me["id"], role=ChatMessageRole.USER, content=f"q{i}"))

    response = client.post("/api/v1/assistant/messages", json={"content": "estourei o limite"})

    assert response.status_code == 429
