"""Modelo de dados final da análise — campos alinhados à seção 20 da especificação
(cs_id, pb_id, interaction_id, ..., model_version, calibration_version)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from gera_d_engine.schemas.evidence import Evidence, EvidenceBasis


class CriterionScore(BaseModel):
    key: Literal[
        "posicionamento",
        "conexao",
        "sondagem",
        "direcionamento",
        "encaminhamento",
        "eficiencia_conducao",
    ]
    label: str
    score: float = Field(ge=0, le=10)
    reading: str = Field(description="Leitura curta, para o dashboard (uma frase).")
    analysis: str = Field(description="Texto detalhado, para a visão detalhada (um parágrafo).")
    evidences: list[Evidence] = Field(default_factory=list)


class PillarScore(BaseModel):
    key: Literal["pilar_93", "pilar_7"]
    label: str
    score: float = Field(ge=0, le=10)
    analysis: str


class ResultPotential(BaseModel):
    """Seção 13 — potencial de geração de resultado para o PB. Não é previsão de receita."""

    level: Literal["Baixo", "Médio", "Médio-alto", "Alto"]
    justification: str


class PbCommercialPotential(BaseModel):
    """Seção 14 — potencial comercial do PB, separado da nota do CS."""

    level: Literal["Baixo", "Médio", "Alto"]
    justification: str
    limitations: str | None = Field(
        default=None,
        description="Registro explícito do que não pôde ser quantificado (seção 14: não inventar potencial).",
    )


class DevelopmentItem(BaseModel):
    """Usado para pontos preservados, riscos e oportunidades perdidas (seção 16)."""

    title: str
    description: str
    basis: EvidenceBasis = EvidenceBasis.EVIDENCIA


class SuggestedQuestion(BaseModel):
    """Seção 6 — perguntas contextuais, não script fixo."""

    question: str
    rationale: str = Field(description="Por que essa pergunta, ligada a que sinal da conversa.")


class TrainingNote(BaseModel):
    """Seção 18 — nota para T&D."""

    competency_to_develop: str
    observed_behavior: str
    expected_behavior: str
    competencies_to_preserve: list[str]


class PbContext(BaseModel):
    """Saída da etapa de construção de contexto do PB (seção 21, passo 4)."""

    seniority_signals: list[str]
    commercial_signals: list[str]
    needs_and_opportunities: list[str]
    availability_notes: str | None = None
    basis_notes: str = Field(
        description="O que é evidência explícita vs. inferência razoável vs. informação insuficiente."
    )


class ConsequenceAnalysis(BaseModel):
    """Saída da etapa de análise de consequência (seção 21, passo 6)."""

    what_was_produced: list[str]
    what_was_missed: list[str]
    narrative: str


class AnalysisResult(BaseModel):
    # Identificação (seção 20)
    cs_id: str
    cs_name: str
    pb_id: str
    pb_name: str
    interaction_id: str
    interaction_date: str
    interaction_type: str
    duration: str | None = None

    # Notas
    scores_by_criterion: list[CriterionScore]
    pilar_93_score: PillarScore
    pilar_7_score: PillarScore
    computed_average: float = Field(
        description="Média simples dos 6 critérios — referência auxiliar, nunca decisão final (seção 12)."
    )
    overall_score: float = Field(ge=0, le=10, description="Julgamento holístico do CS na interação.")
    overall_band_label: str
    overall_classification_text: str

    # Leitura narrativa
    executive_diagnosis: str
    general_reading: str

    # Potenciais
    result_potential: ResultPotential
    pb_commercial_potential: PbCommercialPotential

    # Desenvolvimento
    strengths: list[DevelopmentItem]
    risks: list[DevelopmentItem]
    missed_opportunities: list[DevelopmentItem]
    suggested_questions: list[SuggestedQuestion]
    executive_recommendation: str
    training_recommendation: TrainingNote
    final_evaluation: str

    # Contexto intermediário e evidências (auditoria — seção 22)
    evidence_fragments: list[Evidence]
    pb_context: PbContext
    consequence_analysis: ConsequenceAnalysis

    # Versionamento (obrigatório — seções 20 e 26)
    model_version: str
    calibration_version: str
    generated_at: str
