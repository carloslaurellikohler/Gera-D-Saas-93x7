"""Constantes de domínio do backend (não confundir com calibration/v1.yaml da engine,
que é regra de negócio da análise em si)."""

from __future__ import annotations

import enum


class Objective(str, enum.Enum):
    ONBOARDING = "Onboarding"
    ALINHAMENTO = "Reunião de alinhamento"
    FEEDBACK = "Feedback"
    ENTREVISTA = "Entrevista"
    UM_A_UM = "1:1"
    COMERCIAL = "Reunião comercial"
    AVALIACAO = "Avaliação"
    OUTRO = "Outro"


# Extensões nativamente suportadas por gera_d_engine.ingestion.loader.load_transcript.
# Não ampliar sem antes confirmar suporte na engine (ver plano, seção de riscos: .wav/.m4a).
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".docx": "docx",
    ".txt": "txt",
    ".mp3": "mp3",
    ".mp4": "mp4",
}

ALLOWED_MIME_TYPES: set[str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",  # .txt
    "audio/mpeg",  # .mp3
    "video/mp4",  # .mp4
    "audio/mp4",  # alguns clientes reportam .mp4 de áudio assim
}
