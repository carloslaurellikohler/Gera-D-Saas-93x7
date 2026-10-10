"""Orquestração do ciclo de vida de metodologia/calibração versionada (Fase 7).

Publicar uma nova versão aqui NÃO atualiza o corpus do Assistente de IA (Fase 6): o RAG
indexa só docs/metodologia_93x7.pdf via backend/scripts/ingest_methodology.py, rodado
manualmente. Se o racional da metodologia mudar de fato (não só a calibração técnica),
alguém precisa atualizar o PDF e rodar o script de novo — os dois podem ficar
dessincronizados silenciosamente, por design, nesta fase."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.constants import CriterionKey
from app.models.methodology import Calibrator, FarolColor, Methodology, MethodologyCategory, MethodologyStatus
from app.models.user import User
from app.repositories.methodology_repository import MethodologyRepository
from app.schemas.methodology import MethodologyDraftIn

_EXPECTED_CRITERION_KEYS = {key.value for key in CriterionKey}
_EXPECTED_FAROL_COLORS = {color for color in FarolColor}


class MethodologyNotDraftError(ValueError):
    def __init__(self) -> None:
        super().__init__("Esta ação só é permitida para uma versão em rascunho (DRAFT).")


class MethodologyNotFoundError(ValueError):
    def __init__(self) -> None:
        super().__init__("Versão de metodologia não encontrada.")


class MethodologyCategoryMismatchError(ValueError):
    def __init__(self, missing: set[str], unexpected: set[str]) -> None:
        parts = []
        if missing:
            parts.append(f"faltando: {sorted(missing)}")
        if unexpected:
            parts.append(f"inesperados: {sorted(unexpected)}")
        super().__init__(
            "Os critérios do rascunho não batem com os 6 critérios da metodologia "
            f"({'; '.join(parts)})."
        )


class MethodologyCalibratorMismatchError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "A régua de faixas precisa ter exatamente 4 faixas, uma para cada cor do farol "
            "(verde, amarelo, laranja, vermelho)."
        )


class MethodologyStillReferencedError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "Esta versão já foi usada por uma ou mais análises e não pode ser removida."
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MethodologyService:
    def __init__(self, repo: MethodologyRepository) -> None:
        self.repo = repo

    def list_summaries(self) -> list[Methodology]:
        return self.repo.list_summaries()

    def get(self, methodology_id: uuid.UUID) -> Methodology | None:
        return self.repo.get(methodology_id)

    def get_published(self) -> Methodology | None:
        return self.repo.get_published()

    def create_draft(self, *, from_id: uuid.UUID | None, actor: User) -> Methodology:
        if from_id is not None:
            source = self.repo.get(from_id)
            if source is None:
                raise MethodologyNotFoundError()
            draft = Methodology(
                calibration_version=f"{source.calibration_version} (rascunho {_utcnow():%Y-%m-%d %H:%M:%S})",
                methodology_name=source.methodology_name,
                project=source.project,
                content=dict(source.content),
                created_by_id=actor.id,
                categories=[
                    _clone_category(category) for category in sorted(source.categories, key=lambda c: c.order_index)
                ],
                calibrators=[
                    _clone_calibrator(calibrator)
                    for calibrator in sorted(source.calibrators, key=lambda c: c.order_index)
                ],
            )
        else:
            draft = Methodology(
                calibration_version=f"Nova versão {_utcnow():%Y-%m-%d %H:%M}",
                methodology_name="93x7®",
                project="",
                content={},
                created_by_id=actor.id,
            )
        return self.repo.create(draft)

    def update_draft(self, methodology_id: uuid.UUID, payload: MethodologyDraftIn) -> Methodology:
        methodology = self.repo.get(methodology_id)
        if methodology is None:
            raise MethodologyNotFoundError()
        if methodology.status != MethodologyStatus.DRAFT:
            raise MethodologyNotDraftError()

        updated = self.repo.update_draft(
            methodology_id,
            calibration_version=payload.calibration_version,
            methodology_name=payload.methodology_name,
            project=payload.project,
            content=payload.content,
            categories=[
                {
                    "key": category.key.value,
                    "label": category.label,
                    "description": category.description,
                    "order_index": category.order_index,
                    "extra": category.extra,
                }
                for category in payload.categories
            ],
            calibrators=[
                {
                    "key": calibrator.key,
                    "label": calibrator.label,
                    "color": calibrator.color,
                    "min": calibrator.min,
                    "max": calibrator.max,
                    "order_index": calibrator.order_index,
                }
                for calibrator in payload.calibrators
            ],
        )
        assert updated is not None  # já validamos a existência acima
        return updated

    def publish(self, methodology_id: uuid.UUID) -> Methodology:
        draft = self.repo.get(methodology_id)
        if draft is None:
            raise MethodologyNotFoundError()
        if draft.status != MethodologyStatus.DRAFT:
            raise MethodologyNotDraftError()

        actual_keys = {category.key for category in draft.categories}
        if actual_keys != _EXPECTED_CRITERION_KEYS:
            raise MethodologyCategoryMismatchError(
                missing=_EXPECTED_CRITERION_KEYS - actual_keys, unexpected=actual_keys - _EXPECTED_CRITERION_KEYS
            )

        actual_colors = {calibrator.color for calibrator in draft.calibrators}
        if len(draft.calibrators) != 4 or actual_colors != _EXPECTED_FAROL_COLORS:
            raise MethodologyCalibratorMismatchError()

        return self.repo.publish(methodology_id, published_at=_utcnow())

    def delete_draft(self, methodology_id: uuid.UUID) -> None:
        methodology = self.repo.get(methodology_id)
        if methodology is None:
            return
        if methodology.status != MethodologyStatus.DRAFT:
            raise MethodologyNotDraftError()
        if self.repo.is_referenced_by_analysis(methodology_id):
            raise MethodologyStillReferencedError()
        self.repo.delete_draft(methodology_id)


def _clone_category(category: MethodologyCategory) -> MethodologyCategory:
    return MethodologyCategory(
        key=category.key,
        label=category.label,
        description=category.description,
        order_index=category.order_index,
        extra=dict(category.extra),
    )


def _clone_calibrator(calibrator: Calibrator) -> Calibrator:
    return Calibrator(
        key=calibrator.key,
        label=calibrator.label,
        color=calibrator.color,
        min=calibrator.min,
        max=calibrator.max,
        order_index=calibrator.order_index,
    )
