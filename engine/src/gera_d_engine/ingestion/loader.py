"""Ponto único de entrada da etapa 1 (Ingestão): decide o loader certo pela extensão do arquivo."""

from __future__ import annotations

from pathlib import Path

from gera_d_engine.config import Settings
from gera_d_engine.ingestion.docx_loader import load_docx, load_txt
from gera_d_engine.ingestion.whisper_loader import transcribe_audio_or_video
from gera_d_engine.schemas.transcript import Transcript

_TEXT_EXTENSIONS = {".docx"}
_PLAIN_TEXT_EXTENSIONS = {".txt"}
_AUDIO_VIDEO_EXTENSIONS = {".mp3", ".mp4"}


def load_transcript(file_path: str | Path, settings: Settings) -> Transcript:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in _TEXT_EXTENSIONS:
        return load_docx(path)
    if suffix in _PLAIN_TEXT_EXTENSIONS:
        return load_txt(path)
    if suffix in _AUDIO_VIDEO_EXTENSIONS:
        return transcribe_audio_or_video(path, settings)

    raise ValueError(
        f"Tipo de arquivo não suportado: {suffix}. "
        f"Suportados: {sorted(_TEXT_EXTENSIONS | _PLAIN_TEXT_EXTENSIONS | _AUDIO_VIDEO_EXTENSIONS)}"
    )
