"""Pré-processamento de áudio/vídeo via ffmpeg para contornar o limite hard de 25MB por
arquivo da API Whisper (gera_d_engine.ingestion.whisper_loader chama Whisper 1x por arquivo,
sem chunking, e não pode ser modificada por este módulo — engine/ fica intocada).

Escopo estrito, sinalizado e aprovado pelo usuário: só contorna o limite de tamanho em
.mp3/.mp4 já suportados — não introduz suporte a .wav/.m4a (decisão distinta, que permanece
em ROADMAP.md)."""

from __future__ import annotations

import logging
import math
import subprocess
import tempfile
from pathlib import Path

from gera_d_engine.config import Settings as EngineSettings
from gera_d_engine.ingestion import load_transcript
from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn

log = logging.getLogger(__name__)

WHISPER_MAX_FILE_MB = 25  # limite hard da API da OpenAI, não configurável
_CHUNK_DURATION_SECONDS = 15 * 60  # ~15min; mono 64kbps ≈ 7MB/chunk, com folga generosa
_AUDIO_BITRATE = "64k"
_CHUNKABLE_EXTENSIONS = {".mp3", ".mp4"}
_FFMPEG_TIMEOUT_SECONDS = 1800  # 30min — margem para arquivos de até 1GB


def needs_chunking(file_path: Path) -> bool:
    if file_path.suffix.lower() not in _CHUNKABLE_EXTENSIONS:
        return False  # passthrough: .docx/.txt nunca passam por aqui
    size_mb = file_path.stat().st_size / (1024 * 1024)
    return size_mb > WHISPER_MAX_FILE_MB


def whisper_call_count(file_path: Path, duration_seconds: float | None) -> int:
    """Quantas chamadas ao Whisper a transcrição deste arquivo custa.

    Mora aqui porque é este módulo que conhece o tamanho do chunk. Usado só para
    diagnóstico no FinAI (app/services/analysis_service.py): o faturamento do Whisper é por
    minuto de áudio, então o número de chamadas HTTP não altera o custo.
    """
    if duration_seconds is None or not needs_chunking(file_path):
        return 1
    return max(1, math.ceil(float(duration_seconds) / _CHUNK_DURATION_SECONDS))


def load_transcript_chunked(file_path: Path, engine_settings: EngineSettings) -> Transcript:
    is_video = file_path.suffix.lower() == ".mp4"
    with tempfile.TemporaryDirectory(prefix="gerad-chunks-") as tmp_dir:
        chunk_paths = _extract_and_split(file_path, Path(tmp_dir))
        turns: list[TranscriptTurn] = []
        for i, chunk_path in enumerate(chunk_paths, start=1):
            log.info(
                "transcrevendo chunk %d/%d de %s", i, len(chunk_paths), file_path.name
            )
            turns.extend(load_transcript(chunk_path, engine_settings).turns)

    return Transcript(
        turns=turns,
        is_diarized=False,
        source_kind="video" if is_video else "audio",
        raw_summary=None,
    )


def _extract_and_split(file_path: Path, out_dir: Path) -> list[Path]:
    pattern = str(out_dir / "chunk_%03d.mp3")
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        str(file_path),
        "-vn",
        "-ac",
        "1",
        "-b:a",
        _AUDIO_BITRATE,
        "-f",
        "segment",
        "-segment_time",
        str(_CHUNK_DURATION_SECONDS),
        "-reset_timestamps",
        "1",
        pattern,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=_FFMPEG_TIMEOUT_SECONDS)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg falhou ao processar {file_path.name} (código {exc.returncode})."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"ffmpeg excedeu o tempo limite ao processar {file_path.name}."
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg não encontrado no PATH da imagem do worker.") from exc

    chunks = sorted(out_dir.glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError(f"ffmpeg não gerou nenhum chunk para {file_path.name}.")
    return chunks
