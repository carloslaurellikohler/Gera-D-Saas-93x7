"""Orquestração das 9 etapas do pipeline (seção 21 da especificação).

Etapas 1 (ingestão) e 9 (renderização) ficam fora desta função: ingestão acontece antes, via
`gera_d_engine.ingestion.load_transcript`, e renderização (PDF) acontece depois, via
`gera_d_engine.rendering`. Aqui cuidamos das etapas 2 a 8, que constroem o `AnalysisResult`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from gera_d_engine.calibration import Calibration, load_calibration
from gera_d_engine.config import ENGINE_VERSION, Settings, get_settings
from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.nodes import (
    behavioral_analysis,
    consequence_analysis,
    development,
    fact_extraction,
    normalization,
    pb_context,
    training,
)
from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import InputMetadata, Transcript


def run_pipeline(
    transcript: Transcript,
    metadata: InputMetadata,
    *,
    settings: Settings | None = None,
    calibration: Calibration | None = None,
) -> AnalysisResult:
    settings = settings or get_settings()
    calibration = calibration or load_calibration()

    ctx = PipelineContext(
        transcript=transcript,
        metadata=metadata,
        calibration=calibration,
        settings=settings,
    )

    # Etapa 2 — Normalização
    ctx.transcript = normalization.run(ctx)

    # Etapa 3 — Extração factual
    ctx.fact_extraction = fact_extraction.run(ctx)

    # Etapa 4 — Contexto do PB
    ctx.pb_context_output = pb_context.run(ctx)

    # Etapa 5 — Análise comportamental (6 critérios + Pilar 93/7)
    ctx.behavioral = behavioral_analysis.run(ctx)

    # Etapa 6 — Análise de consequência + nota final holística
    ctx.consequence = consequence_analysis.run(ctx)

    # Etapa 7 — Desenvolvimento
    ctx.development = development.run(ctx)

    # Etapa 8 — T&D e avaliação final
    ctx.training = training.run(ctx)

    return _assemble_result(ctx)


def _assemble_result(ctx: PipelineContext) -> AnalysisResult:
    """Etapa 9 (parte de dados) — monta o AnalysisResult final. Puramente determinística: nenhum
    campo aqui é decidido pelo LLM nesta função, apenas agregado e formatado."""

    assert ctx.fact_extraction and ctx.pb_context_output and ctx.behavioral
    assert ctx.consequence and ctx.development and ctx.training

    scores = ctx.behavioral.scores_by_criterion
    computed_average = round(sum(c.score for c in scores) / len(scores), 2) if scores else 0.0
    overall_score = ctx.consequence.overall_score
    band = ctx.calibration.classify_band(overall_score)

    evidence_fragments = [ev for criterion in scores for ev in criterion.evidences]

    return AnalysisResult(
        cs_id=ctx.metadata.cs_id,
        cs_name=ctx.metadata.cs_name,
        pb_id=ctx.metadata.pb_id,
        pb_name=ctx.metadata.pb_name,
        interaction_id=ctx.metadata.interaction_id,
        interaction_date=ctx.metadata.interaction_date,
        interaction_type=ctx.metadata.interaction_type,
        duration=ctx.metadata.duration or "Não informada na transcrição",
        scores_by_criterion=scores,
        pilar_93_score=ctx.behavioral.pilar_93_score,
        pilar_7_score=ctx.behavioral.pilar_7_score,
        computed_average=computed_average,
        overall_score=overall_score,
        overall_band_label=band.label,
        overall_classification_text=ctx.development.overall_classification_text,
        executive_diagnosis=ctx.development.executive_diagnosis,
        general_reading=ctx.development.general_reading,
        result_potential=ctx.consequence.result_potential,
        pb_commercial_potential=ctx.pb_context_output.pb_commercial_potential,
        strengths=ctx.development.strengths,
        risks=ctx.development.risks,
        missed_opportunities=ctx.development.missed_opportunities,
        suggested_questions=ctx.development.suggested_questions,
        executive_recommendation=ctx.development.executive_recommendation,
        training_recommendation=ctx.training.training_recommendation,
        final_evaluation=ctx.training.final_evaluation,
        evidence_fragments=evidence_fragments,
        pb_context=ctx.pb_context_output.pb_context,
        consequence_analysis=ctx.consequence.consequence_analysis,
        model_version=ENGINE_VERSION,
        calibration_version=ctx.calibration.calibration_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
