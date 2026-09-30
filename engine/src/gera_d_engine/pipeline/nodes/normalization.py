"""Etapa 2 — Normalização.

Quando a transcrição já chega diarizada (texto com falas identificadas, ex.: exemplo1.docx), a
normalização é apenas uma passagem de limpeza — determinística, sem custo de LLM. Quando vem de
Whisper sem diarização, usa o LLM para inferir prováveis trocas de falante a partir do conteúdo e
de eventuais dicas de nomes (InputMetadata), sem nunca inventar uma diarização confiável: quando o
modelo não tiver segurança, mantém `speaker=None` no turno.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble
from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn


class _InferredTurn(BaseModel):
    speaker: str | None = Field(
        default=None,
        description="Nome do provável falante (CS ou PB), ou null se não houver segurança razoável.",
    )
    text: str


class _NormalizationOutput(BaseModel):
    turns: list[_InferredTurn]
    is_diarized: bool = Field(
        description="True somente se a maioria dos turnos pôde ser atribuída com segurança razoável."
    )


def run(ctx: PipelineContext) -> Transcript:
    transcript = ctx.transcript

    if transcript.is_diarized:
        cleaned = [
            TranscriptTurn(speaker=t.speaker, text=t.text.strip())
            for t in transcript.turns
            if t.text.strip()
        ]
        return Transcript(
            turns=cleaned,
            is_diarized=True,
            source_kind=transcript.source_kind,
            raw_summary=transcript.raw_summary,
        )

    # Transcrição sem diarização (tipicamente vinda do Whisper). Tenta inferir via LLM.
    model = build_chat_model(ctx.settings).with_structured_output(_NormalizationOutput)
    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: NORMALIZAÇÃO\n"
        "Você recebe segmentos cronológicos de uma transcrição de áudio/vídeo SEM diarização "
        "(não sabemos quem fala cada trecho). Você conhece os nomes dos dois participantes: "
        f"CS = {ctx.metadata.cs_name}, PB = {ctx.metadata.pb_name}.\n"
        "Tente inferir, pelo conteúdo (quem se apresenta, quem faz perguntas de onboarding, quem "
        "responde sobre a própria carreira, etc.), qual segmento pertence a qual participante. "
        "Se não houver sinal razoável para um segmento, deixe `speaker` como null — NÃO adivinhe. "
        "Marque `is_diarized=true` apenas se a maioria dos segmentos puder ser atribuída com "
        "segurança razoável; caso contrário, `is_diarized=false`."
    )
    segments_text = "\n".join(f"[{i}] {t.text}" for i, t in enumerate(transcript.turns))
    human = f"SEGMENTOS:\n{segments_text}"

    result = model.invoke([("system", system), ("human", human)])

    turns = [TranscriptTurn(speaker=t.speaker, text=t.text) for t in result.turns]
    return Transcript(
        turns=turns,
        is_diarized=result.is_diarized,
        source_kind=transcript.source_kind,
        raw_summary=transcript.raw_summary,
    )
