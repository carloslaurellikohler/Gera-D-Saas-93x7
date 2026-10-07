"""Orquestração de trilhas de treinamento (LearningPath, Fase 5). A recomendação lê
scores_by_criterion (via MetricsRepository, já existente) para identificar os critérios
com pior média nas análises recentes do próprio usuário — nunca os campos de texto
livre da engine (training_recommendation/risks), que não garantem corresponder a um
dos 6 critérios enumerados. Recomendação é sempre pessoal, nunca agregada (mesmo para
ADMIN) — diferente do padrão Dashboard/Métricas."""

from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from datetime import date, timedelta

from app.core.constants import CriterionKey
from app.models.learning_path import LearningPath
from app.models.user import User
from app.repositories.content_repository import ContentRepository
from app.repositories.learning_path_enrollment_repository import LearningPathEnrollmentRepository
from app.repositories.learning_path_repository import LearningPathRepository
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.content import ContentResponse
from app.schemas.learning_path import (
    CreateLearningPathRequest,
    EnrolledLearningPathSummary,
    EnrollmentResponse,
    LearningPathDetail,
    LearningPathItemResponse,
    LearningPathSummary,
    UpdateLearningPathRequest,
)

_RECOMMENDATION_WINDOW_DAYS = 90
_SCORE_CUTOFF = 7.0
_CRITERION_VALUES = {key.value for key in CriterionKey}


class NotEnrolledError(ValueError):
    def __init__(self) -> None:
        super().__init__("Você precisa se inscrever na trilha antes de concluir um material.")


class LearningPathItemNotFoundError(ValueError):
    def __init__(self) -> None:
        super().__init__("Material não encontrado nesta trilha.")


class LearningPathService:
    def __init__(
        self,
        repo: LearningPathRepository,
        content_repo: ContentRepository,
        metrics_repo: MetricsRepository,
        enrollment_repo: LearningPathEnrollmentRepository,
    ) -> None:
        self.repo = repo
        self.content_repo = content_repo
        self.metrics_repo = metrics_repo
        self.enrollment_repo = enrollment_repo

    def create(self, *, request: CreateLearningPathRequest, created_by: User) -> LearningPathDetail:
        for item in request.items:
            if self.content_repo.get(item.content_id) is None:
                raise ValueError(f"Material {item.content_id} não encontrado.")

        learning_path = LearningPath(
            title=request.title,
            description=request.description,
            criterion_key=request.criterion_key,
            estimated_duration_minutes=request.estimated_duration_minutes,
            created_by_id=created_by.id,
        )
        learning_path = self.repo.create(
            learning_path, items=[(i.content_id, i.order_index) for i in request.items]
        )
        return self.get_detail(learning_path.id)  # type: ignore[return-value]

    def update(
        self, learning_path_id: uuid.UUID, *, request: UpdateLearningPathRequest
    ) -> LearningPathDetail | None:
        if self.repo.get(learning_path_id) is None:
            return None
        for item in request.items:
            if self.content_repo.get(item.content_id) is None:
                raise ValueError(f"Material {item.content_id} não encontrado.")

        self.repo.update(
            learning_path_id,
            title=request.title,
            description=request.description,
            criterion_key=request.criterion_key,
            estimated_duration_minutes=request.estimated_duration_minutes,
            items=[(i.content_id, i.order_index) for i in request.items],
        )
        return self.get_detail(learning_path_id)

    def get_detail(
        self, learning_path_id: uuid.UUID, *, current_user: User | None = None
    ) -> LearningPathDetail | None:
        learning_path = self.repo.get(learning_path_id)
        if learning_path is None:
            return None
        rows = self.repo.list_items(learning_path_id)

        completed_item_ids: set[uuid.UUID] = set()
        if current_user is not None:
            enrollment = self.enrollment_repo.get_enrollment(
                user_id=current_user.id, learning_path_id=learning_path_id
            )
            if enrollment is not None:
                completed_item_ids = self.enrollment_repo.completed_item_ids(enrollment.id)

        return LearningPathDetail(
            id=learning_path.id,
            title=learning_path.title,
            description=learning_path.description,
            criterion_key=learning_path.criterion_key,
            estimated_duration_minutes=learning_path.estimated_duration_minutes,
            created_at=learning_path.created_at,
            updated_at=learning_path.updated_at,
            items=[
                LearningPathItemResponse(
                    id=item.id,
                    content=ContentResponse.model_validate(content),
                    order_index=item.order_index,
                    completed=item.id in completed_item_ids,
                )
                for item, content in rows
            ],
        )

    def list_all(self) -> list[LearningPathSummary]:
        return [self._to_summary(lp) for lp in self.repo.list()]

    def enroll(self, *, learning_path_id: uuid.UUID, user: User) -> EnrollmentResponse | None:
        if self.repo.get(learning_path_id) is None:
            return None
        enrollment = self.enrollment_repo.enroll(user_id=user.id, learning_path_id=learning_path_id)
        return EnrollmentResponse(learning_path_id=learning_path_id, enrolled_at=enrollment.enrolled_at)

    def list_enrolled(self, *, user: User) -> list[EnrolledLearningPathSummary]:
        rows = self.enrollment_repo.list_enrolled_with_paths(user.id)
        summaries = []
        for enrollment, learning_path in rows:
            total = self.repo.count_items(learning_path.id)
            completed = self.enrollment_repo.count_completed(enrollment.id)
            progress = round((completed / total) * 100, 1) if total else 0.0
            summaries.append(
                EnrolledLearningPathSummary(
                    id=learning_path.id,
                    title=learning_path.title,
                    description=learning_path.description,
                    criterion_key=learning_path.criterion_key,
                    estimated_duration_minutes=learning_path.estimated_duration_minutes,
                    item_count=total,
                    completed_count=completed,
                    progress_percent=progress,
                    is_completed=total > 0 and completed == total,
                    enrolled_at=enrollment.enrolled_at,
                    created_at=learning_path.created_at,
                )
            )
        return summaries

    def mark_item_complete(self, *, learning_path_id: uuid.UUID, item_id: uuid.UUID, user: User) -> None:
        enrollment = self.enrollment_repo.get_enrollment(
            user_id=user.id, learning_path_id=learning_path_id
        )
        if enrollment is None:
            raise NotEnrolledError()
        item = self.repo.get_item(learning_path_id=learning_path_id, item_id=item_id)
        if item is None:
            raise LearningPathItemNotFoundError()
        self.enrollment_repo.mark_item_complete(enrollment_id=enrollment.id, learning_path_item_id=item_id)

    def unmark_item_complete(self, *, learning_path_id: uuid.UUID, item_id: uuid.UUID, user: User) -> None:
        enrollment = self.enrollment_repo.get_enrollment(
            user_id=user.id, learning_path_id=learning_path_id
        )
        if enrollment is None:
            return
        self.enrollment_repo.unmark_item_complete(
            enrollment_id=enrollment.id, learning_path_item_id=item_id
        )

    def get_recommended(self, *, current_user: User, limit: int = 3) -> list[LearningPathSummary]:
        since = date.today() - timedelta(days=_RECOMMENDATION_WINDOW_DAYS)
        rows = self.metrics_repo.completed_rows(owner_ids=[current_user.id], since=since)
        if not rows:
            return []

        averages = _criterion_averages(rows)
        weak_keys = [
            CriterionKey(key)
            for key, avg in sorted(averages.items(), key=lambda kv: kv[1])
            if avg < _SCORE_CUTOFF and key in _CRITERION_VALUES
        ]
        if not weak_keys:
            return []

        candidates = self.repo.list_by_criterion_keys(weak_keys)
        order = {key: idx for idx, key in enumerate(weak_keys)}
        candidates.sort(key=lambda lp: order[lp.criterion_key])
        return [self._to_summary(lp) for lp in candidates[:limit]]

    def delete(self, learning_path_id: uuid.UUID) -> None:
        self.repo.delete(learning_path_id)

    def _to_summary(self, learning_path: LearningPath) -> LearningPathSummary:
        return LearningPathSummary(
            id=learning_path.id,
            title=learning_path.title,
            description=learning_path.description,
            criterion_key=learning_path.criterion_key,
            estimated_duration_minutes=learning_path.estimated_duration_minutes,
            item_count=self.repo.count_items(learning_path.id),
            created_at=learning_path.created_at,
            updated_at=learning_path.updated_at,
        )


def _criterion_averages(rows) -> dict[str, float]:
    scores: dict[str, list[float]] = defaultdict(list)
    for _, result in rows:
        for item in (result or {}).get("scores_by_criterion", []):
            key, score = item.get("key"), item.get("score")
            if key is not None and score is not None:
                scores[key].append(score)
    return {key: statistics.mean(values) for key, values in scores.items()}
