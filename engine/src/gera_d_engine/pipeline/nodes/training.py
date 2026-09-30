"""Etapa 8 — Nota para T&D e avaliação final (seção 18)."""

from __future__ import annotations

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble, format_transcript_block
from gera_d_engine.schemas.steps import TrainingOutput


def run(ctx: PipelineContext) -> TrainingOutput:
    raw = ctx.calibration.raw
    model = build_chat_model(ctx.settings).with_structured_output(TrainingOutput)

    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: T&D E AVALIAÇÃO FINAL\n"
        f"{raw['training_notes_rule'].strip()} Preencha: competência a desenvolver, comportamento "
        "observado, comportamento esperado e uma lista de competências a preservar (o que já "
        "funciona bem e não deve ser perdido).\n\n"
        "Escreva também `final_evaluation`: um parágrafo de fechamento que resume a avaliação "
        "geral do CS nesta interação, coerente com a nota final e a classificação já definidas."
    )

    behavioral_summary = ctx.behavioral.model_dump_json(indent=2) if ctx.behavioral else "{}"
    consequence_summary = ctx.consequence.model_dump_json(indent=2) if ctx.consequence else "{}"
    development_summary = ctx.development.model_dump_json(indent=2) if ctx.development else "{}"
    human = (
        f"CS: {ctx.metadata.cs_name} | PB: {ctx.metadata.pb_name}\n\n"
        f"NOTAS POR CRITÉRIO E PILARES:\n{behavioral_summary}\n\n"
        f"ANÁLISE DE CONSEQUÊNCIA:\n{consequence_summary}\n\n"
        f"DESENVOLVIMENTO:\n{development_summary}\n\n"
        + format_transcript_block(ctx.transcript.as_plain_text(), ctx.transcript.raw_summary)
    )
    return model.invoke([("system", system), ("human", human)])
