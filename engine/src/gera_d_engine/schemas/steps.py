"""Schemas de saída estruturada de cada etapa de IA do pipeline (seção 21).

Cada etapa usa `ChatOpenAI(...).with_structured_output(<Output>)`, garantindo JSON validado em
vez de texto livre. As etapas de código puro (ingestão, normalização determinística, renderização)
não têm schema de "output de LLM" aqui.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from gera_d_engine.schemas.analysis import (
    ConsequenceAnalysis,
    CriterionScore,
    DevelopmentItem,
    PbCommercialPotential,
    PbContext,
    PillarScore,
    ResultPotential,
    SuggestedQuestion,
    TrainingNote,
)


class FactExtractionOutput(BaseModel):
    """Etapa 3 — extração factual."""

    relevant_statements: list[str] = Field(description="Falas relevantes para a avaliação, resumidas.")
    questions_asked: list[str] = Field(description="Perguntas feitas pelo CS ao PB.")
    commitments: list[str] = Field(description="Compromissos assumidos por qualquer uma das partes.")
    opportunities_mentioned: list[str] = Field(description="Oportunidades comerciais citadas na conversa.")
    values_mentioned: list[str] = Field(description="Valores, percentuais ou números citados.")
    products_discussed: list[str] = Field(description="Produtos/temas discutidos.")
    dates_mentioned: list[str] = Field(description="Datas ou prazos citados.")
    experience_signals: list[str] = Field(description="Sinais de experiência/trajetória do PB.")


class PbContextOutput(BaseModel):
    """Etapa 4 — construção de contexto do PB."""

    pb_context: PbContext
    pb_commercial_potential: PbCommercialPotential


class BehavioralAnalysisOutput(BaseModel):
    """Etapa 5 — análise comportamental do CS: os 6 critérios + Pilar 93 / Pilar 7."""

    scores_by_criterion: list[CriterionScore] = Field(min_length=6, max_length=6)
    pilar_93_score: PillarScore
    pilar_7_score: PillarScore


class ConsequenceAnalysisOutput(BaseModel):
    """Etapa 6 — análise de consequência. Recebe as notas da etapa 5 como contexto e determina o
    overall_score de forma holística (seção 12: não é média cega; considera a consequência real)."""

    consequence_analysis: ConsequenceAnalysis
    result_potential: ResultPotential
    overall_score: float = Field(ge=0, le=10)
    overall_justification: str


class DevelopmentOutput(BaseModel):
    """Etapa 7 — desenvolvimento: síntese narrativa + pontos acionáveis."""

    executive_diagnosis: str = Field(description="2-3 frases para a Visão Executiva.")
    general_reading: str = Field(description="1-2 parágrafos para a Visão Detalhada.")
    overall_classification_text: str = Field(
        description='Frase curta de classificação, ex.: "Atenção: boa base relacional e técnica, ...".'
    )
    strengths: list[DevelopmentItem]
    risks: list[DevelopmentItem]
    missed_opportunities: list[DevelopmentItem]
    suggested_questions: list[SuggestedQuestion]
    executive_recommendation: str


class TrainingOutput(BaseModel):
    """Etapa 8 — T&D e avaliação final (fecha ambos os relatórios)."""

    training_recommendation: TrainingNote
    final_evaluation: str
