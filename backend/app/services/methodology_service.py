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
from app.models.methodology import (
    Calibrator,
    FarolColor,
    Methodology,
    MethodologyAnchor,
    MethodologyAnchorExample,
    MethodologyCategory,
    MethodologyEligibilityRule,
    MethodologyStatus,
    MethodologySubdimension,
)
from app.models.user import User
from app.repositories.methodology_repository import MethodologyRepository
from app.schemas.methodology import ANCHOR_LEVELS, PILLAR_KEYS, MethodologyDraftIn

_EXPECTED_CRITERION_KEYS = {key.value for key in CriterionKey}
_EXPECTED_FAROL_COLORS = {color for color in FarolColor}
_EXPECTED_ANCHOR_LEVELS = set(ANCHOR_LEVELS)

# A soma dos pesos é comparada com 1 em ponto flutuante vindo de Numeric(5,4): a
# tolerância absorve o arredondamento da conversão, não erro de preenchimento.
_WEIGHT_SUM_TOLERANCE = 1e-6


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


class MethodologyAnchorMismatchError(ValueError):
    """A régua observável é o que impede a IA de arbitrar a nota (Manual V2.1, seção 3:
    "o modelo não pode atribuir notas dos pilares livremente"). Publicar sem ela
    devolveria o produto à arbitrariedade que a V2.1 existe para eliminar."""

    def __init__(self, scope_key: str, missing: set[int], unexpected: set[int]) -> None:
        parts = []
        if missing:
            parts.append(f"faltando: {sorted(missing)}")
        if unexpected:
            parts.append(f"inesperados: {sorted(unexpected)}")
        super().__init__(
            f"As âncoras de '{scope_key}' precisam cobrir exatamente os níveis "
            f"{list(ANCHOR_LEVELS)} ({'; '.join(parts)})."
        )


class MethodologyWeightSumError(ValueError):
    def __init__(self, total: float) -> None:
        super().__init__(
            "Os pesos dos 6 critérios precisam somar 100%; a soma atual é "
            f"{total * 100:.2f}%."
        )


class MethodologyBandCoverageError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"A régua de faixas precisa cobrir de 0 a 10 sem buraco nem sobreposição ({detail}).")


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
                anchors=[_clone_anchor(a) for a in sorted(source.anchors, key=lambda a: a.order_index)],
                anchor_examples=[
                    _clone_anchor_example(e) for e in sorted(source.anchor_examples, key=lambda e: e.order_index)
                ],
                subdimensions=[
                    _clone_subdimension(s) for s in sorted(source.subdimensions, key=lambda s: s.order_index)
                ],
                eligibility_rules=[
                    _clone_eligibility_rule(r) for r in sorted(source.eligibility_rules, key=lambda r: r.order_index)
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
            content=payload.content.model_dump(exclude_none=True),
            categories=[
                {
                    "key": category.key.value,
                    "label": category.label,
                    "description": category.description,
                    "order_index": category.order_index,
                    "central_question": category.central_question,
                    "what_it_is_not": category.what_it_is_not,
                    "positive_evidence": category.positive_evidence,
                    "negative_evidence": category.negative_evidence,
                    "cross_impact_text": category.cross_impact_text,
                    "weight": category.weight,
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
            anchors=[
                {
                    "scope": anchor.scope,
                    "scope_key": anchor.scope_key,
                    "level": anchor.level,
                    "descriptor": anchor.descriptor,
                    "order_index": anchor.order_index,
                }
                for anchor in payload.anchors
            ],
            anchor_examples=[
                {
                    "criterion_key": example.criterion_key.value,
                    "level": example.level,
                    "scenario": example.scenario,
                    "quote": example.quote,
                    "rationale": example.rationale,
                    "order_index": example.order_index,
                }
                for example in payload.anchor_examples
            ],
            subdimensions=[
                {
                    "criterion_key": sub.criterion_key.value,
                    "name": sub.name,
                    "levels": sub.levels,
                    "order_index": sub.order_index,
                }
                for sub in payload.subdimensions
            ],
            eligibility_rules=[
                {
                    "scope_key": rule.scope_key,
                    "condition": rule.condition,
                    "effect": rule.effect,
                    "max_score": rule.max_score,
                    "order_index": rule.order_index,
                }
                for rule in payload.eligibility_rules
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

        _validate_band_coverage(draft)
        _validate_weights(draft)
        _validate_anchors(draft)

        return self.repo.publish(methodology_id, published_at=_utcnow())

    def build_prompt_preview(self, methodology: Methodology) -> dict:
        """Import local: engine_integration é a única camada que conhece gera_d_engine, e
        importá-la no topo faria todo o service carregar a engine só por causa da prévia."""
        from app.engine_integration.prompt_preview import build_prompt_preview

        return build_prompt_preview(methodology)

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
        central_question=category.central_question,
        what_it_is_not=category.what_it_is_not,
        positive_evidence=category.positive_evidence,
        negative_evidence=category.negative_evidence,
        cross_impact_text=category.cross_impact_text,
        weight=category.weight,
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


def _validate_band_coverage(draft: Methodology) -> None:
    """As faixas precisam cobrir [0, 10] sem buraco nem sobreposição. Sem isso,
    Calibration.classify_band cai no fallback silencioso `score_bands[-1]` e uma nota
    legítima recebe a cor errada no farol. A faixa mais baixa usa um min sentinela
    negativo (-999 no seed original) justamente para fechar o fundo da escala, então a
    cobertura é checada a partir de 0."""
    bands = sorted(draft.calibrators, key=lambda c: c.min)
    for band in bands:
        if band.min > band.max:
            raise MethodologyBandCoverageError(f"a faixa '{band.label}' tem mínimo maior que o máximo")
    if bands[0].min > 0:
        raise MethodologyBandCoverageError(f"nada cobre as notas abaixo de {bands[0].min}")
    if bands[-1].max < 10:
        raise MethodologyBandCoverageError(f"nada cobre as notas acima de {bands[-1].max}")
    for lower, upper in zip(bands, bands[1:]):
        if upper.min <= lower.max:
            raise MethodologyBandCoverageError(f"'{lower.label}' e '{upper.label}' se sobrepõem")
        # Faixas são contíguas em passos de 0,1 (ex.: 6,9 → 7,0); folga maior é buraco.
        if round(upper.min - lower.max, 2) > 0.1:
            raise MethodologyBandCoverageError(f"há um buraco entre '{lower.label}' e '{upper.label}'")


def _validate_weights(draft: Methodology) -> None:
    total = sum(float(category.weight) for category in draft.categories)
    if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
        raise MethodologyWeightSumError(total)


def _validate_anchors(draft: Methodology) -> None:
    levels_by_scope: dict[str, set[int]] = {}
    for anchor in draft.anchors:
        levels_by_scope.setdefault(anchor.scope_key, set()).add(anchor.level)

    expected_scopes = sorted(_EXPECTED_CRITERION_KEYS) + list(PILLAR_KEYS)
    for scope_key in expected_scopes:
        actual = levels_by_scope.get(scope_key, set())
        if actual != _EXPECTED_ANCHOR_LEVELS:
            raise MethodologyAnchorMismatchError(
                scope_key=scope_key,
                missing=_EXPECTED_ANCHOR_LEVELS - actual,
                unexpected=actual - _EXPECTED_ANCHOR_LEVELS,
            )


def _clone_anchor(anchor: MethodologyAnchor) -> MethodologyAnchor:
    return MethodologyAnchor(
        scope=anchor.scope,
        scope_key=anchor.scope_key,
        level=anchor.level,
        descriptor=anchor.descriptor,
        order_index=anchor.order_index,
    )


def _clone_anchor_example(example: MethodologyAnchorExample) -> MethodologyAnchorExample:
    return MethodologyAnchorExample(
        criterion_key=example.criterion_key,
        level=example.level,
        scenario=example.scenario,
        quote=example.quote,
        rationale=example.rationale,
        order_index=example.order_index,
    )


def _clone_subdimension(subdimension: MethodologySubdimension) -> MethodologySubdimension:
    return MethodologySubdimension(
        criterion_key=subdimension.criterion_key,
        name=subdimension.name,
        levels=list(subdimension.levels),
        order_index=subdimension.order_index,
    )


def _clone_eligibility_rule(rule: MethodologyEligibilityRule) -> MethodologyEligibilityRule:
    return MethodologyEligibilityRule(
        scope_key=rule.scope_key,
        condition=rule.condition,
        effect=rule.effect,
        max_score=rule.max_score,
        order_index=rule.order_index,
    )
