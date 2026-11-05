"""Schemas de request/response da metodologia versionada.

Desde a Fase 9 o JSONB `content` deixou de ser `dict` livre e passou por
MethodologyContentIn: toda chave global que pipeline/prompts.py ou pipeline/nodes/*.py
leem da calibração está declarada aqui. Isso move a falha de "KeyError no meio de uma
análise paga" para "422/409 na hora de salvar o rascunho" — a engine acessa `raw["chave"]`
direto, sem default, e o calibration_builder não valida nada."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import CriterionKey
from app.models.methodology import AnchorScope, EligibilityEffect, FarolColor, MethodologyStatus

# Níveis da escala 0–10 que precisam de âncora (Manual V2.1, seção 8). Os ímpares e o 0
# ficam de fora de propósito: a progressão completa 0..10 é descrita uma única vez, no
# bloco global da escala, e as âncoras marcam os cinco pontos de calibração.
ANCHOR_LEVELS: tuple[int, ...] = (2, 4, 6, 8, 10)

# Chaves de pilar aceitas em MethodologyAnchor.scope_key quando scope=PILLAR; precisam
# casar com content.pillars, que é o que a engine lê em nodes/behavioral_analysis.py.
PILLAR_KEYS: tuple[str, ...] = ("pilar_93", "pilar_7")

SUBDIMENSION_LEVEL_COUNT = 5


class PillarIn(BaseModel):
    label: str
    description: str


class PillarsIn(BaseModel):
    pilar_93: PillarIn
    pilar_7: PillarIn
    rule: str


class EvidenceBasisIn(BaseModel):
    evidencia: str
    inferencia_razoavel: str
    informacao_insuficiente: str
    rule: str


class ResultPotentialIn(BaseModel):
    description: str
    levels: list[str] = Field(min_length=1)
    # Nunca lida por nenhum nó, mas preservada: é dado da metodologia, não do prompt.
    rule: str | None = None


class PbCommercialPotentialIn(BaseModel):
    description: str
    levels: list[str] = Field(min_length=1)
    warning: str


class DevelopmentTaxonomyIn(BaseModel):
    pontos_preservados: str
    riscos: str
    oportunidades_perdidas: str


class MethodologyContentIn(BaseModel):
    """Os blocos globais do prompt. Cada campo aqui é lido literalmente por
    build_system_preamble() ou por um nó do pipeline — ver o mapa em
    engine_integration/calibration_builder.py."""

    model_config = ConfigDict(extra="allow")  # tolera chaves de versões futuras/antigas

    # Preâmbulo comum a todas as 7 etapas (pipeline/prompts.py)
    objective: str
    unit_of_analysis: str
    product_principle: str
    contextual_analysis_principle: str
    seniority_and_adaptation: str
    individual_development_not_ranking: str
    forbidden_behaviors: list[str] = Field(min_length=1)
    evidence_basis: EvidenceBasisIn

    # Etapa 5 — análise comportamental
    pillars: PillarsIn
    evidence_structure: str

    # Etapa 6 — consequência e nota final
    final_score_rule: str
    result_potential: ResultPotentialIn

    # Etapa 4 — contexto do PB
    pb_commercial_potential: PbCommercialPotentialIn

    # Etapa 7 — desenvolvimento
    development_taxonomy: DevelopmentTaxonomyIn
    suggested_questions_rule: str
    suggested_questions_examples: list[str] = Field(min_length=1)
    executive_recommendation_rule: str

    # Etapa 8 — T&D
    training_notes_rule: str

    # Lidos fora dos prompts (Calibration.format_score_line) ou puramente documentais
    score_format: str = "● {nota} | {criterio}"
    object_evaluated: str | None = None


class MethodologyAnchorIn(BaseModel):
    scope: AnchorScope
    scope_key: str
    level: int
    descriptor: str
    order_index: int

    @model_validator(mode="after")
    def _check_scope_key(self) -> "MethodologyAnchorIn":
        if self.scope is AnchorScope.PILLAR and self.scope_key not in PILLAR_KEYS:
            raise ValueError(f"scope_key de pilar precisa ser um de {PILLAR_KEYS}; recebido {self.scope_key!r}.")
        if self.scope is AnchorScope.CRITERION and self.scope_key not in {k.value for k in CriterionKey}:
            raise ValueError(f"scope_key de critério precisa ser uma CriterionKey; recebido {self.scope_key!r}.")
        if self.level not in ANCHOR_LEVELS:
            raise ValueError(f"nível de âncora precisa ser um de {ANCHOR_LEVELS}; recebido {self.level}.")
        return self


class MethodologyAnchorExampleIn(BaseModel):
    criterion_key: CriterionKey
    level: int
    scenario: str | None = None
    quote: str | None = None
    rationale: str
    order_index: int

    @model_validator(mode="after")
    def _check_level(self) -> "MethodologyAnchorExampleIn":
        if self.level not in ANCHOR_LEVELS:
            raise ValueError(f"nível de exemplo precisa ser um de {ANCHOR_LEVELS}; recebido {self.level}.")
        return self


class MethodologySubdimensionIn(BaseModel):
    criterion_key: CriterionKey
    name: str
    levels: list[str]
    order_index: int

    @model_validator(mode="after")
    def _check_levels(self) -> "MethodologySubdimensionIn":
        if len(self.levels) != SUBDIMENSION_LEVEL_COUNT:
            raise ValueError(
                f"a rubrica de uma subdimensão precisa ter exatamente {SUBDIMENSION_LEVEL_COUNT} "
                f"níveis (0 a 4); '{self.name}' tem {len(self.levels)}."
            )
        if any(not level.strip() for level in self.levels):
            raise ValueError(f"a subdimensão '{self.name}' tem nível vazio.")
        return self


class MethodologyEligibilityRuleIn(BaseModel):
    scope_key: str
    condition: str
    effect: EligibilityEffect
    max_score: float | None = None
    order_index: int

    @model_validator(mode="after")
    def _check_effect(self) -> "MethodologyEligibilityRuleIn":
        valid_scopes = {k.value for k in CriterionKey} | {"TRANSVERSAL"}
        if self.scope_key not in valid_scopes:
            raise ValueError(f"scope_key precisa ser uma CriterionKey ou 'TRANSVERSAL'; recebido {self.scope_key!r}.")
        if self.effect is EligibilityEffect.CAP:
            if self.max_score is None:
                raise ValueError("uma regra CAP precisa de max_score.")
            if not 0 <= self.max_score <= 10:
                raise ValueError(f"max_score precisa estar entre 0 e 10; recebido {self.max_score}.")
        elif self.max_score is not None:
            raise ValueError("uma regra NOTE não pode ter max_score.")
        return self


class MethodologyCategoryIn(BaseModel):
    key: CriterionKey
    label: str
    description: str
    order_index: int
    # Definição refinada (Manual V2.1, seção 4)
    central_question: str | None = None
    what_it_is_not: str | None = None
    positive_evidence: str | None = None
    negative_evidence: str | None = None
    cross_impact_text: str | None = None
    # Peso na nota geral ponderada; soma dos 6 validada em MethodologyService.publish()
    weight: float = Field(default=0.0, ge=0, le=1)
    extra: dict[str, str] = Field(default_factory=dict)


class CalibratorIn(BaseModel):
    key: str
    label: str
    color: FarolColor
    min: float
    max: float
    order_index: int


class MethodologyDraftIn(BaseModel):
    calibration_version: str
    methodology_name: str
    project: str
    content: MethodologyContentIn
    categories: list[MethodologyCategoryIn]
    calibrators: list[CalibratorIn]
    anchors: list[MethodologyAnchorIn] = Field(default_factory=list)
    anchor_examples: list[MethodologyAnchorExampleIn] = Field(default_factory=list)
    subdimensions: list[MethodologySubdimensionIn] = Field(default_factory=list)
    eligibility_rules: list[MethodologyEligibilityRuleIn] = Field(default_factory=list)


class CreateMethodologyDraftRequest(BaseModel):
    from_id: uuid.UUID | None = None


class MethodologySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calibration_version: str
    methodology_name: str
    status: MethodologyStatus
    created_at: datetime
    published_at: datetime | None
    archived_at: datetime | None


class MethodologyDetail(MethodologySummary):
    project: str
    content: dict
    categories: list[MethodologyCategoryIn]
    calibrators: list[CalibratorIn]
    anchors: list[MethodologyAnchorIn]
    anchor_examples: list[MethodologyAnchorExampleIn]
    subdimensions: list[MethodologySubdimensionIn]
    eligibility_rules: list[MethodologyEligibilityRuleIn]


class MethodologyPromptPreview(BaseModel):
    """O texto exato que a engine receberá como system prompt — o que permite ao ADMIN
    conferir a régua compilada antes de publicar, em vez de descobrir numa análise paga."""

    calibration_version: str
    system_preamble: str
    criteria_block: str
