"""Transcrição de áudio (.mp3) e vídeo (.mp4) via Whisper API.

A API não faz diarização: o resultado sai como segmentos cronológicos sem falante identificado
(is_diarized=False). A etapa de normalização do pipeline é responsável por tentar inferir a troca
de turnos a partir do conteúdo, com o apoio de eventuais dicas de participantes (InputMetadata).
"""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from gera_d_engine.config import Settings
from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn

SUPPORTED_AUDIO_VIDEO_EXTENSIONS = {".mp3", ".mp4"}


def transcribe_audio_or_video(file_path: str | Path, settings: Settings) -> Transcript:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_AUDIO_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Extensão não suportada para transcrição: {path.suffix}. "
            f"Suportadas: {sorted(SUPPORTED_AUDIO_VIDEO_EXTENSIONS)}"
        )

    client = OpenAI(api_key=settings.openai_api_key)
    with path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
        )

    segments = getattr(response, "segments", None) or []
    turns = [
        TranscriptTurn(speaker=None, text=segment.text.strip())
        for segment in segments
        if getattr(segment, "text", "").strip()
    ]
    if not turns:
        text = (getattr(response, "text", "") or "").strip()
        turns = [TranscriptTurn(speaker=None, text=text)] if text else []

    source_kind = "video" if path.suffix.lower() == ".mp4" else "audio"
    return Transcript(turns=turns, is_diarized=False, source_kind=source_kind, raw_summary=None)
