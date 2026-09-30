"""Estado acumulado ao longo das 9 etapas do pipeline (seção 21 da especificação)."""

from __future__ import annotations

from dataclasses import dataclass

from gera_d_engine.calibration import Calibration
from gera_d_engine.config import Settings
from gera_d_engine.schemas.steps import (
    BehavioralAnalysisOutput,
    ConsequenceAnalysisOutput,
    DevelopmentOutput,
    FactExtractionOutput,
    PbContextOutput,
    TrainingOutput,
)
from gera_d_engine.schemas.transcript import InputMetadata, Transcript


@dataclass
class PipelineContext:
    transcript: Transcript
    metadata: InputMetadata
    calibration: Calibration
    settings: Settings

    fact_extraction: FactExtractionOutput | None = None
    pb_context_output: PbContextOutput | None = None
    behavioral: BehavioralAnalysisOutput | None = None
    consequence: ConsequenceAnalysisOutput | None = None
    development: DevelopmentOutput | None = None
    training: TrainingOutput | None = None
