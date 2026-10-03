from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.chat_message import ChatMessage, ChatMessageRole
from app.models.user import User, UserRole, UserStatus
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U1", email="cmru1@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def other_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U2", email="cmru2@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


def test_create_and_list_all_in_chronological_order(db_session, regular_user):
    base = datetime.now(timezone.utc)
    repo = ChatMessageRepository(db_session)
    repo.create(
        ChatMessage(user_id=regular_user.id, role=ChatMessageRole.USER, content="primeira", created_at=base)
    )
    repo.create(
        ChatMessage(
            user_id=regular_user.id,
            role=ChatMessageRole.ASSISTANT,
            content="segunda",
            created_at=base + timedelta(seconds=1),
        )
    )

    messages = repo.list_all(user_id=regular_user.id)

    assert [m.content for m in messages] == ["primeira", "segunda"]


def test_list_all_is_scoped_to_user(db_session, regular_user, other_user):
    repo = ChatMessageRepository(db_session)
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.USER, content="minha"))
    repo.create(ChatMessage(user_id=other_user.id, role=ChatMessageRole.USER, content="do outro"))

    assert [m.content for m in repo.list_all(user_id=regular_user.id)] == ["minha"]
    assert [m.content for m in repo.list_all(user_id=other_user.id)] == ["do outro"]


def test_list_recent_respects_limit_and_order(db_session, regular_user):
    # created_at é setado explicitamente (em vez de depender do server_default=now())
    # porque a fixture db_session roda o teste inteiro numa única transação real do
    # Postgres via savepoints — now() fica congelado no mesmo valor para todos os
    # commits deste teste, o que tornaria o ORDER BY created_at indeterminado.
    base = datetime.now(timezone.utc)
    repo = ChatMessageRepository(db_session)
    for i in range(5):
        repo.create(
            ChatMessage(
                user_id=regular_user.id,
                role=ChatMessageRole.USER,
                content=f"msg-{i}",
                created_at=base + timedelta(seconds=i),
            )
        )

    recent = repo.list_recent(user_id=regular_user.id, limit=3)

    assert [m.content for m in recent] == ["msg-2", "msg-3", "msg-4"]


def test_count_today_only_counts_user_role(db_session, regular_user):
    repo = ChatMessageRepository(db_session)
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.USER, content="pergunta"))
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.ASSISTANT, content="resposta"))

    since = datetime.now(timezone.utc) - timedelta(hours=1)

    assert repo.count_today(user_id=regular_user.id, since=since) == 1


def test_count_today_respects_midnight_boundary(db_session, regular_user):
    repo = ChatMessageRepository(db_session)
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.USER, content="ontem ou hoje"))

    future_since = datetime.now(timezone.utc) + timedelta(hours=1)

    assert repo.count_today(user_id=regular_user.id, since=future_since) == 0


def test_count_today_is_scoped_to_user(db_session, regular_user, other_user):
    repo = ChatMessageRepository(db_session)
    repo.create(ChatMessage(user_id=other_user.id, role=ChatMessageRole.USER, content="do outro"))

    since = datetime.now(timezone.utc) - timedelta(hours=1)

    assert repo.count_today(user_id=regular_user.id, since=since) == 0
