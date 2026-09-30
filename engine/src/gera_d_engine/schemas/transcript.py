"""Modelos de entrada: transcrição normalizada e metadados fornecidos pelo chamador."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InputMetadata(BaseModel):
    """Metadados que o chamador (CLI / futuro backend) fornece sobre a interação.

    A transcrição por si só nem sempre contém IDs formais de CRM — em produção esses campos
    viriam do sistema que originou a chamada. Aqui eles chegam explicitamente na ingestão.
    """

    cs_id: str
    cs_name: str
    pb_id: str
    pb_name: str
    interaction_id: str
    interaction_date: str  # ISO date (YYYY-MM-DD)
    interaction_type: str  # ex.: "Onboarding / Boas-vindas"
    duration: str | None = None  # ex.: "42 min" — None quando não informada


class TranscriptTurn(BaseModel):
    """Um turno de fala. `speaker` fica `None` quando a origem não permite diarização
    (ex.: Whisper sem diarização) — nesse caso a normalização tenta inferir via LLM."""

    speaker: str | None = None
    text: str


class Transcript(BaseModel):
    """Transcrição normalizada, pronta para a etapa de extração factual."""

    turns: list[TranscriptTurn]
    is_diarized: bool = Field(
        description="True quando os turnos já vêm com falante identificado de forma confiável."
    )
    source_kind: str  # "texto_transcrito" | "audio" | "video"
    raw_summary: str | None = None  # resumo/contexto que já vinha junto do input (ex.: exemplo1.docx)

    def as_plain_text(self) -> str:
        lines = []
        for turn in self.turns:
            prefix = f"{turn.speaker}: " if turn.speaker else ""
            lines.append(f"{prefix}{turn.text}")
        return "\n".join(lines)
