"""Rotas do Assistente de IA (Fase 6). Sempre pessoal — escopado ao usuário autenticado,
nunca agregado entre usuários, mesmo para ADMIN (mesmo princípio de learning_paths.py).
Síncrono, sem Celery: é uma única chamada LLM, não o pipeline pesado da engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_assistant_service, get_current_user
from app.models.user import User
from app.schemas.assistant import ChatHistoryResponse, ChatMessageResponse, SendChatMessageRequest
from app.services.assistant_service import AssistantService, DailyMessageLimitError

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/messages", response_model=ChatHistoryResponse)
def get_chat_history(
    service: AssistantService = Depends(get_assistant_service),
    current_user: User = Depends(get_current_user),
):
    messages = service.list_history(user=current_user)
    return ChatHistoryResponse(
        messages=[ChatMessageResponse.model_validate(m) for m in messages]
    )


@router.post("/messages", response_model=ChatMessageResponse, status_code=201)
def send_chat_message(
    request: SendChatMessageRequest,
    service: AssistantService = Depends(get_assistant_service),
    current_user: User = Depends(get_current_user),
):
    try:
        message = service.ask(user=current_user, content=request.content)
    except DailyMessageLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return ChatMessageResponse.model_validate(message)
