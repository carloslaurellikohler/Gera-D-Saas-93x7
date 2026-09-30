"""Etapa 4 — Construção de contexto do PB (seções 10, 13 e 14 da especificação)."""

from __future__ import annotations

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble, format_transcript_block
from gera_d_engine.schemas.steps import PbContextOutput


def run(ctx: PipelineContext) -> PbContextOutput:
    model = build_chat_model(ctx.settings).with_structured_output(PbContextOutput)
    calib = ctx.calibration.raw["pb_commercial_potential"]
    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: CONTEXTO DO PB\n"
        "A partir da transcrição e dos fatos já extraídos, construa o contexto do PB: sinais de "
        "senioridade/experiência, sinais comerciais (carteira, rede, relacionamentos, acesso a "
        "decisores), necessidades e oportunidades identificadas, e notas sobre disponibilidade "
        "quando mencionada. Em seguida, classifique o potencial comercial do PB "
        f"({calib['description'].strip()}) em um destes níveis: {calib['levels']}. "
        f"{calib['warning'].strip()} Se a transcrição não permitir quantificar algo (carteira, "
        "disponibilidade, volume de oportunidades), registre isso explicitamente no campo "
        "`limitations` — nunca invente."
    )
    fact_summary = ctx.fact_extraction.model_dump_json(indent=2) if ctx.fact_extraction else "{}"
    human = (
        f"PB: {ctx.metadata.pb_name} | Tipo de interação: {ctx.metadata.interaction_type}\n\n"
        f"FATOS JÁ EXTRAÍDOS:\n{fact_summary}\n\n"
        + format_transcript_block(ctx.transcript.as_plain_text(), ctx.transcript.raw_summary)
    )
    return model.invoke([("system", system), ("human", human)])
