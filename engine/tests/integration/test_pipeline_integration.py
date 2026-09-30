"""Teste de ponta a ponta contra a API da OpenAI de verdade.

Roda o pipeline completo sobre docs/exemplo1.docx e valida a FORMA do resultado (schema,
critérios presentes, notas na faixa válida, PDFs gerados) — não o texto exato, já que a saída é
generativa. Requer OPENAI_API_KEY configurada; caso contrário, é pulado.

    pytest tests/integration -m slow
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gera_d_engine.calibration import load_calibration
from gera_d_engine.config import get_settings
from gera_d_engine.ingestion.docx_loader import load_docx
from gera_d_engine.pipeline import run_pipeline
from gera_d_engine.rendering import export_both
from gera_d_engine.schemas.transcript import InputMetadata

EXAMPLE_DOCX = Path(__file__).resolve().parents[3] / "docs" / "exemplo1.docx"

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
def _skip_without_api_key():
    if not get_settings().openai_api_key:
        pytest.skip("OPENAI_API_KEY não configurada — pulando teste de integração.")


def test_full_pipeline_on_example_transcript(tmp_path):
    settings = get_settings()
    calibration = load_calibration()

    transcript = load_docx(EXAMPLE_DOCX)
    metadata = InputMetadata(
        cs_id="alexandre_marques",
        cs_name="Alexandre Marques",
        pb_id="francibele_ratzlaff",
        pb_name="Francibele Ratzlaff",
        interaction_id="integration-test-001",
        interaction_date="2026-01-15",
        interaction_type="Onboarding / Boas-vindas",
        duration=None,
    )

    result = run_pipeline(transcript, metadata, settings=settings, calibration=calibration)

    assert len(result.scores_by_criterion) == 6
    assert {c.key for c in result.scores_by_criterion} == {
        "posicionamento",
        "conexao",
        "sondagem",
        "direcionamento",
        "encaminhamento",
        "eficiencia_conducao",
    }
    for criterion in result.scores_by_criterion:
        assert 0 <= criterion.score <= 10

    assert 0 <= result.pilar_93_score.score <= 10
    assert 0 <= result.pilar_7_score.score <= 10
    assert 0 <= result.overall_score <= 10
    assert result.calibration_version == calibration.calibration_version

    executivo_path, detalhado_path = export_both(result, calibration, tmp_path)
    assert executivo_path.exists()
    assert detalhado_path.exists()
