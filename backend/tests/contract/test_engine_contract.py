"""Trava barata contra mudanças silenciosas na API pública da engine que o backend
depende (adapter.py, mappers.py). Não chama a OpenAI — só introspecção de assinaturas
e de campos obrigatórios dos schemas pydantic."""

from __future__ import annotations

import inspect

from gera_d_engine.ingestion import load_transcript
from gera_d_engine.pipeline import run_pipeline
from gera_d_engine.rendering import export_both
from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import InputMetadata, Transcript
from gera_d_engine.storage.repository import ReportRepository


def test_load_transcript_signature():
    params = list(inspect.signature(load_transcript).parameters)
    assert params[:2] == ["file_path", "settings"]


def test_run_pipeline_signature():
    params = inspect.signature(run_pipeline).parameters
    assert list(params)[:2] == ["transcript", "metadata"]
    assert "settings" in params
    assert "calibration" in params


def test_export_both_signature():
    params = list(inspect.signature(export_both).parameters)
    assert params[:3] == ["result", "calibration", "out_dir"]


def test_input_metadata_required_fields():
    required = {
        name for name, field in InputMetadata.model_fields.items() if field.is_required()
    }
    assert required == {
        "cs_id",
        "cs_name",
        "pb_id",
        "pb_name",
        "interaction_id",
        "interaction_date",
        "interaction_type",
    }


def test_transcript_required_fields():
    required = {name for name, field in Transcript.model_fields.items() if field.is_required()}
    assert {"turns", "is_diarized", "source_kind"}.issubset(required)


def test_analysis_result_required_fields_include_core_identity_and_versioning():
    required = {
        name for name, field in AnalysisResult.model_fields.items() if field.is_required()
    }
    assert {
        "cs_id",
        "cs_name",
        "pb_id",
        "pb_name",
        "interaction_id",
        "interaction_date",
        "interaction_type",
        "scores_by_criterion",
        "overall_score",
        "model_version",
        "calibration_version",
        "generated_at",
    }.issubset(required)


def test_report_repository_protocol_methods():
    assert hasattr(ReportRepository, "save")
    assert hasattr(ReportRepository, "load")
