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


class CriterionKey(str, enum.Enum):
    """Espelha CriterionScore.key da engine (scores_by_criterion), por duplicação
    intencional — a engine nunca é importada fora de engine_integration/. Usado para
    casar materiais/trilhas (Fase 5) com os critérios de pior desempenho do usuário."""

    POSICIONAMENTO = "posicionamento"
    CONEXAO = "conexao"
    SONDAGEM = "sondagem"
    DIRECIONAMENTO = "direcionamento"
    ENCAMINHAMENTO = "encaminhamento"
    EFICIENCIA_CONDUCAO = "eficiencia_conducao"


# Formatos aceitos para materiais de apoio da biblioteca (Fase 5) — distinto de
# ALLOWED_EXTENSIONS (uploads de análise). v1 restrito a PDF; vídeo-aula entra como
# external_url (kind=LINK), não upload direto.
ALLOWED_CONTENT_EXTENSIONS: dict[str, str] = {
    ".pdf": "pdf",
}
