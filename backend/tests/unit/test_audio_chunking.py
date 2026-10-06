from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn

from app.engine_integration import audio_chunking


def test_needs_chunking_false_for_text_extensions_even_if_large(tmp_path: Path):
    big_txt = tmp_path / "transcricao.txt"
    big_txt.write_bytes(b"x" * (30 * 1024 * 1024))
    assert audio_chunking.needs_chunking(big_txt) is False


def test_needs_chunking_false_for_small_audio_video(tmp_path: Path):
    small_mp3 = tmp_path / "chamada.mp3"
    small_mp3.write_bytes(b"ID3" + b"\x00" * 100)
    assert audio_chunking.needs_chunking(small_mp3) is False


def test_needs_chunking_true_for_large_audio_video(tmp_path: Path):
    big_mp4 = tmp_path / "video.mp4"
    big_mp4.write_bytes(b"\x00" * (audio_chunking.WHISPER_MAX_FILE_MB + 1) * 1024 * 1024)
    assert audio_chunking.needs_chunking(big_mp4) is True


def test_load_transcript_chunked_merges_turns_in_order(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"\x00")

    chunk_1 = tmp_path / "chunk_000.mp3"
    chunk_2 = tmp_path / "chunk_001.mp3"
    chunk_1.write_bytes(b"\x00")
    chunk_2.write_bytes(b"\x00")

    monkeypatch.setattr(
        audio_chunking, "_extract_and_split", lambda file_path, out_dir: [chunk_1, chunk_2]
    )

    transcripts_by_chunk = {
        chunk_1: Transcript(
            turns=[TranscriptTurn(speaker=None, text="primeira parte")],
            is_diarized=False,
            source_kind="audio",
        ),
        chunk_2: Transcript(
            turns=[TranscriptTurn(speaker=None, text="segunda parte")],
            is_diarized=False,
            source_kind="audio",
        ),
    }
    monkeypatch.setattr(
        audio_chunking,
        "load_transcript",
        lambda path, settings: transcripts_by_chunk[path],
    )

    result = audio_chunking.load_transcript_chunked(video_path, MagicMock())

    assert [turn.text for turn in result.turns] == ["primeira parte", "segunda parte"]
    assert result.source_kind == "video"
    assert result.is_diarized is False


def test_extract_and_split_raises_runtime_error_on_ffmpeg_failure(tmp_path: Path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["ffmpeg"], stderr=b"boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        audio_chunking._extract_and_split(tmp_path / "video.mp4", tmp_path)


def test_extract_and_split_raises_runtime_error_when_ffmpeg_missing(tmp_path: Path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        audio_chunking._extract_and_split(tmp_path / "video.mp4", tmp_path)
