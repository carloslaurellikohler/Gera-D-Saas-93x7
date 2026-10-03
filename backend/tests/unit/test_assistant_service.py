from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.models.analysis import Analysis, AnalysisStatus
from app.models.chat_message import ChatMessage, ChatMessageRole
from app.models.methodology_chunk import MethodologyChunk
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.methodology_chunk_repository import MethodologyChunkRepository
from app.repositories.user_repository import UserRepository
from app.services.assistant_service import AssistantService, DailyMessageLimitError


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U1", email="asu1@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def other_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U2", email="asu2@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def fake_chat_model() -> MagicMock:
    model = MagicMock()
    model.invoke.return_value = MagicMock(content="resposta do assistente")
    return model


@pytest.fixture()
def fake_embedding_model() -> MagicMock:
    model = MagicMock()
    model.embed_query.return_value = [1.0, 0.0]
    return model


@pytest.fixture()
def service(db_session, fake_chat_model, fake_embedding_model) -> AssistantService:
    return AssistantService(
        chat_repo=ChatMessageRepository(db_session),
        chunk_repo=MethodologyChunkRepository(db_session),
        metrics_repo=MetricsRepository(db_session),
        settings=Settings(ASSISTANT_DAILY_MESSAGE_LIMIT=3, ASSISTANT_TOP_K_CHUNKS=1),
        chat_model=fake_chat_model,
        embedding_model=fake_embedding_model,
    )


def test_ask_persists_user_and_assistant_messages(service, regular_user):
    reply = service.ask(user=regular_user, content="O que é o Pilar 7?")

    history = service.list_history(user=regular_user)
    assert [m.role for m in history] == [ChatMessageRole.USER, ChatMessageRole.ASSISTANT]
    assert history[0].content == "O que é o Pilar 7?"
    assert reply.content == "resposta do assistente"
    assert reply.role == ChatMessageRole.ASSISTANT


def test_ask_raises_when_daily_limit_reached(service, regular_user, db_session):
    repo = ChatMessageRepository(db_session)
    for i in range(3):
        repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.USER, content=f"q{i}"))

    with pytest.raises(DailyMessageLimitError):
        service.ask(user=regular_user, content="mais uma pergunta")


def test_ask_rate_limit_does_not_count_assistant_replies(service, regular_user, db_session):
    repo = ChatMessageRepository(db_session)
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.ASSISTANT, content="a1"))
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.ASSISTANT, content="a2"))
    repo.create(ChatMessage(user_id=regular_user.id, role=ChatMessageRole.ASSISTANT, content="a3"))

    # Limite é 3, mas nenhuma é role=USER — não deve bloquear.
    service.ask(user=regular_user, content="primeira pergunta")


def test_history_and_rate_limit_are_scoped_to_user(service, regular_user, other_user, db_session):
    repo = ChatMessageRepository(db_session)
    for i in range(3):
        repo.create(ChatMessage(user_id=other_user.id, role=ChatMessageRole.USER, content=f"q{i}"))

    # other_user estourou o limite, mas regular_user não deve ser afetado.
    service.ask(user=regular_user, content="minha pergunta")

    assert len(service.list_history(user=regular_user)) == 2
    assert len(service.list_history(user=other_user)) == 3


def test_top_chunks_picks_highest_cosine_similarity(service, regular_user, db_session, fake_embedding_model):
    chunk_repo = MethodologyChunkRepository(db_session)
    chunk_repo.replace_all(
        [
            MethodologyChunk(chunk_index=0, content="irrelevante", embedding=[0.0, 1.0]),
            MethodologyChunk(chunk_index=1, content="relevante", embedding=[1.0, 0.0]),
        ]
    )
    fake_embedding_model.embed_query.return_value = [1.0, 0.0]

    top = service._top_chunks([1.0, 0.0], k=1)

    assert [c.content for c in top] == ["relevante"]


def test_personal_context_never_includes_raw_transcript(service, regular_user, db_session):
    analysis_result = {
        "overall_score": 8.0,
        "scores_by_criterion": [{"key": "sondagem", "label": "Sondagem", "score": 6.0}],
        "training_recommendation": "texto livre que não deve aparecer no resumo",
    }
    AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id="ctx-1",
            user_id=regular_user.id,
            status=AnalysisStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            transcription={"turns": ["texto bruto da conversa que nunca deve ser lido pelo assistente"]},
            analysis_result=analysis_result,
        )
    )

    context = service._personal_context(regular_user)

    assert "sondagem" in context
    assert "texto livre que não deve aparecer" not in context
    assert "texto bruto da conversa" not in context


def test_personal_context_without_completed_analyses(service, regular_user):
    context = service._personal_context(regular_user)

    assert "não tem análises concluídas" in context
