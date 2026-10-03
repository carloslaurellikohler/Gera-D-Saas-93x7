"""Teste end-to-end real do EngineAdapter (load_transcript -> run_pipeline -> export_reports)
contra a API da OpenAI de verdade — chama o pipeline completo (6-7 chamadas LLM + render de PDF),
o que tem custo real. Espelha o padrão do teste de integração da própria engine
(engine/tests/integration/test_pipeline_integration.py), mas com uma guarda mais rígida:
NÃO basta OPENAI_API_KEY estar presente no ambiente (isso pode acontecer sem intenção — a engine
tem seu próprio load_dotenv() que, dependendo do contexto de import, pode encontrar
engine/.env mesmo quando o processo roda a partir de backend/). É preciso exportar
GERAD_RUN_ENGINE_SMOKE_TEST=1 explicitamente para rodar este teste. Nunca faz parte da suíte
padrão (excluído via -m "not slow" no pyproject.toml)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from gera_d_engine.calibration import load_calibration

from app.engine_integration.adapter import EngineAdapter
from app.engine_integration.mappers import build_input_metadata
from app.models.analysis import Analysis

pytestmark = pytest.mark.slow


@pytest.fixture()
def _skip_without_explicit_opt_in():
    if os.getenv("GERAD_RUN_ENGINE_SMOKE_TEST") != "1":
        pytest.skip(
            "Pulado por padrão — chama a API da OpenAI de verdade e tem custo. "
            "Rode com GERAD_RUN_ENGINE_SMOKE_TEST=1 pytest -m slow para executar deliberadamente."
        )
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY não definido no ambiente")


def test_adapter_full_flow_against_real_openai(_skip_without_explicit_opt_in, tmp_path: Path):
    input_file = tmp_path / "transcricao.txt"
    input_file.write_text(
        "CS: Oi João, tudo bem? Vamos começar nosso onboarding hoje.\n"
        "PB: Oi, tudo certo! Pode começar.\n"
        "CS: Legal, me conta um pouco sobre o que você espera do produto.\n"
        "PB: Quero entender como configurar os relatórios principais.\n",
        encoding="utf-8",
    )

    adapter = EngineAdapter(calibration=load_calibration(), methodology_id=uuid.uuid4())
    analysis = Analysis(
        participant_name="João Silva",
        objective="Onboarding",
        input_type="txt",
        interaction_id="adapter-smoke-test",
    )
    metadata = build_input_metadata(analysis, cs_id="cs-1", cs_name="Consultor GerAD")

    transcript = adapter.load_transcript(input_file)
    result = adapter.run_pipeline(transcript, metadata)
    executivo_path, detalhado_path = adapter.export_reports(result, tmp_path / "reports")

    assert result.pb_name == "João Silva"
    assert 0 <= result.overall_score <= 10
    assert executivo_path.exists()
    assert detalhado_path.exists()
