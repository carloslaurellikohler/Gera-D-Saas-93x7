"""Medição de duração de áudio via ffprobe (FinAI).

Política de erro oposta à de audio_chunking: aqui qualquer falha devolve None e a análise
segue — contabilizar custo nunca reprova nada.
"""

from __future__ import annotations

import subprocess
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.ai_cost import audio
from app.ai_cost.audio import probe_duration_seconds


def _fake_run(stdout: bytes) -> MagicMock:
    return MagicMock(return_value=MagicMock(stdout=stdout))


def test_devolve_duracao_em_segundos(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(subprocess, "run", _fake_run(b"934.512000\n"))

    assert probe_duration_seconds(tmp_path / "chamada.mp3") == Decimal("934.512000")


@pytest.mark.parametrize(
    "erro",
    [
        FileNotFoundError("ffprobe"),
        subprocess.CalledProcessError(1, "ffprobe"),
        subprocess.TimeoutExpired("ffprobe", 60),
    ],
)
def test_qualquer_falha_do_ffprobe_devolve_none(monkeypatch, tmp_path: Path, erro):
    monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=erro))

    assert probe_duration_seconds(tmp_path / "chamada.mp3") is None


def test_saida_nao_numerica_devolve_none(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(subprocess, "run", _fake_run(b"N/A\n"))

    assert probe_duration_seconds(tmp_path / "chamada.mp3") is None


def test_duracao_zero_devolve_none(monkeypatch, tmp_path: Path):
    """Arquivo sem trilha de áudio: não há minuto a cobrar, e 0 viraria custo zero com
    status PRICED — enganoso. None leva a cost_status=NO_UNITS."""
    monkeypatch.setattr(subprocess, "run", _fake_run(b"0.000000\n"))

    assert probe_duration_seconds(tmp_path / "video_sem_audio.mp4") is None


def test_passa_o_timeout_configurado(monkeypatch, tmp_path: Path):
    run = _fake_run(b"10.0\n")
    monkeypatch.setattr(subprocess, "run", run)

    probe_duration_seconds(tmp_path / "chamada.mp3", timeout_seconds=7)

    assert run.call_args.kwargs["timeout"] == 7
    assert run.call_args.args[0][0] == "ffprobe"
