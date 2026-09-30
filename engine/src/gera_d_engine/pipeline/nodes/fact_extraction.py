"""Etapa 3 — Extração factual."""

from __future__ import annotations

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble, format_transcript_block
from gera_d_engine.schemas.steps import FactExtractionOutput


def run(ctx: PipelineContext) -> FactExtractionOutput:
    model = build_chat_model(ctx.settings).with_structured_output(FactExtractionOutput)
    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: EXTRAÇÃO FACTUAL\n"
        "Extraia da transcrição apenas o que foi de fato dito — falas relevantes, perguntas feitas "
        "pelo CS, compromissos assumidos por qualquer parte, oportunidades comerciais mencionadas, "
        "valores/percentuais citados, produtos discutidos, datas/prazos citados e sinais de "
        "experiência do PB. Não interprete nem avalie ainda — apenas extraia."
    )
    human = (
        f"CS: {ctx.metadata.cs_name} | PB: {ctx.metadata.pb_name} | "
        f"Tipo de interação: {ctx.metadata.interaction_type}\n\n"
        + format_transcript_block(ctx.transcript.as_plain_text(), ctx.transcript.raw_summary)
    )
    return model.invoke([("system", system), ("human", human)])
