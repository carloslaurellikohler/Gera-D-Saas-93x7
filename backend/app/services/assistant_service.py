"""Orquestração do Assistente de IA (Fase 6). Responde só com base em (a) chunks da
metodologia 93x7® recuperados por similaridade em memória e (b) contexto pessoal
estruturado das análises COMPLETED do próprio usuário (via MetricsRepository) — nunca
agregado entre usuários, mesmo para ADMIN (mesmo princípio de LearningPathService).
NUNCA usa transcription/analysis_result bruto no prompt, só scores_by_criterion/
overall_score/overall_band_label já extraídos pelo MetricsRepository."""

from __future__ import annotations

import math
import statistics
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import Settings
from app.models.chat_message import ChatMessage, ChatMessageRole
from app.models.methodology_chunk import MethodologyChunk
from app.models.user import User
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.methodology_chunk_repository import MethodologyChunkRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.services.assistant_llm import build_assistant_chat_model, build_embedding_model

_PERSONAL_CONTEXT_WINDOW_DAYS = 90

_SYSTEM_PROMPT = """Você é o Assistente de IA do GerAD, uma plataforma de avaliação de \
qualidade em atendimento comercial que aplica a metodologia proprietária 93x7®.

Seu papel é responder (a) dúvidas sobre a metodologia 93x7®, usando os trechos da \
metodologia fornecidos abaixo, e (b) perguntas pessoais do usuário sobre as próprias \
análises já concluídas, usando o resumo de desempenho fornecido abaixo.

Regras importantes:
- Responda apenas com base no conteúdo fornecido neste prompt (trechos da metodologia \
e resumo pessoal). Nunca invente números, critérios ou recomendações que não estejam \
nesse conteúdo.
- Você apoia a avaliação do gestor, nunca a substitui — não dê veredictos definitivos \
sobre desempenho, apenas contextualize com base nos dados fornecidos.
- Se a pergunta não puder ser respondida com o conteúdo fornecido, diga isso claramente \
em vez de especular.
- Responda em português do Brasil, de forma objetiva e profissional."""


class DailyMessageLimitError(ValueError):
    def __init__(self) -> None:
        super().__init__("Você atingiu o limite de perguntas de hoje. Volte amanhã.")


class AssistantService:
    def __init__(
        self,
        chat_repo: ChatMessageRepository,
        chunk_repo: MethodologyChunkRepository,
        metrics_repo: MetricsRepository,
        user_repo: UserRepository,
        settings: Settings,
        chat_model: ChatOpenAI | None = None,
        embedding_model: OpenAIEmbeddings | None = None,
    ) -> None:
        self.chat_repo = chat_repo
        self.chunk_repo = chunk_repo
        self.metrics_repo = metrics_repo
        self.user_repo = user_repo
        self.settings = settings
        self._chat_model = chat_model
        self._embedding_model = embedding_model

    @property
    def chat_model(self) -> ChatOpenAI:
        if self._chat_model is None:
            self._chat_model = build_assistant_chat_model(self.settings)
        return self._chat_model

    @property
    def embedding_model(self) -> OpenAIEmbeddings:
        if self._embedding_model is None:
            self._embedding_model = build_embedding_model(self.settings)
        return self._embedding_model

    def list_history(self, *, user: User) -> list[ChatMessage]:
        return self.chat_repo.list_all(user_id=user.id, conversation_id=user.current_assistant_conversation_id)

    def start_new_conversation(self, *, user: User) -> None:
        self.user_repo.update(user.id, current_assistant_conversation_id=uuid.uuid4())

    def ask(self, *, user: User, content: str) -> ChatMessage:
        self._check_rate_limit(user)
        conversation_id = user.current_assistant_conversation_id
        self.chat_repo.create(
            ChatMessage(
                user_id=user.id, role=ChatMessageRole.USER, content=content, conversation_id=conversation_id
            )
        )

        question_embedding = self.embedding_model.embed_query(content)
        relevant_chunks = self._top_chunks(question_embedding, k=self.settings.ASSISTANT_TOP_K_CHUNKS)
        personal_context = self._personal_context(user)
        history = self.chat_repo.list_recent(
            user_id=user.id, conversation_id=conversation_id, limit=self.settings.ASSISTANT_HISTORY_WINDOW
        )

        prompt_messages = self._build_prompt(relevant_chunks, personal_context, history)
        answer = self.chat_model.invoke(prompt_messages)
        answer_text = answer.content if isinstance(answer.content, str) else str(answer.content)

        return self.chat_repo.create(
            ChatMessage(
                user_id=user.id,
                role=ChatMessageRole.ASSISTANT,
                content=answer_text,
                conversation_id=conversation_id,
            )
        )

    def _check_rate_limit(self, user: User) -> None:
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.chat_repo.count_today(user_id=user.id, since=start_of_day)
        if count >= self.settings.ASSISTANT_DAILY_MESSAGE_LIMIT:
            raise DailyMessageLimitError()

    def _top_chunks(self, question_embedding: list[float], *, k: int) -> list[MethodologyChunk]:
        chunks = self.chunk_repo.list_all()
        if not chunks:
            return []
        scored = [(_cosine_similarity(question_embedding, chunk.embedding), chunk) for chunk in chunks]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]

    def _personal_context(self, user: User) -> str:
        """Resumo textual curto a partir de scores_by_criterion/overall_score/farol já
        extraídos — nunca o texto bruto (transcription/analysis_result) da engine."""
        since = date.today() - timedelta(days=_PERSONAL_CONTEXT_WINDOW_DAYS)
        rows = self.metrics_repo.completed_rows(owner_ids=[user.id], since=since)
        if not rows:
            return "O usuário ainda não tem análises concluídas nos últimos 90 dias."

        overall_scores = [
            (result or {}).get("overall_score")
            for _, result in rows
            if (result or {}).get("overall_score") is not None
        ]
        criterion_scores: dict[str, list[float]] = defaultdict(list)
        for _, result in rows:
            for item in (result or {}).get("scores_by_criterion", []):
                key, score = item.get("key"), item.get("score")
                if key is not None and score is not None:
                    criterion_scores[key].append(score)

        lines = [f"O usuário tem {len(rows)} análise(s) concluída(s) nos últimos 90 dias."]
        if overall_scores:
            lines.append(f"Nota geral média: {statistics.mean(overall_scores):.1f}.")
        for key, scores in criterion_scores.items():
            lines.append(f"Critério '{key}': média {statistics.mean(scores):.1f} ({len(scores)} análise(s)).")
        return " ".join(lines)

    def _build_prompt(
        self,
        chunks: list[MethodologyChunk],
        personal_context: str,
        history: list[ChatMessage],
    ) -> list[tuple[str, str]]:
        methodology_context = (
            "\n\n".join(chunk.content for chunk in chunks)
            if chunks
            else "Nenhum trecho da metodologia foi encontrado para esta pergunta."
        )
        system_content = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"--- Trechos da metodologia 93x7® ---\n{methodology_context}\n\n"
            f"--- Resumo pessoal do usuário ---\n{personal_context}"
        )
        messages: list[tuple[str, str]] = [("system", system_content)]
        for message in history:
            role = "human" if message.role == ChatMessageRole.USER else "ai"
            messages.append((role, message.content))
        return messages


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
