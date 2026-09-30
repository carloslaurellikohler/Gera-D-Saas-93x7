"""Etapa 6 — Análise de consequência + nota final holística (seções 12 e 13)."""

from __future__ import annotations

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble, format_transcript_block
from gera_d_engine.schemas.steps import ConsequenceAnalysisOutput


def run(ctx: PipelineContext) -> ConsequenceAnalysisOutput:
    raw = ctx.calibration.raw
    model = build_chat_model(ctx.settings).with_structured_output(ConsequenceAnalysisOutput)

    result_potential = raw["result_potential"]
    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: ANÁLISE DE CONSEQUÊNCIA E NOTA FINAL\n"
        "Com base nas notas por critério já calculadas, determine o que a condução do CS "
        "efetivamente produziu (ou deixou de produzir) para o PB: liste `what_was_produced` e "
        "`what_was_missed`, e escreva uma narrativa curta amarrando os dois.\n\n"
        "Em seguida, classifique o potencial de geração de resultado para o PB "
        f"({result_potential['description'].strip()}) em um destes níveis: "
        f"{result_potential['levels']}, sempre com justificativa.\n\n"
        f"REGRA DA NOTA FINAL: {raw['final_score_rule'].strip()}\n"
        "Produza `overall_score` (0 a 10, uma casa decimal) como julgamento holístico — NÃO é a "
        "média aritmética das notas por critério. Leve em conta se a conversa realmente produziu "
        "avanço (Encaminhamento/consequência), mesmo quando Posicionamento e Conexão são altos. "
        "Justifique em `overall_justification`, citando explicitamente quando e por que a nota "
        "final se afasta da média simples dos critérios."
    )

    scores_summary = ctx.behavioral.model_dump_json(indent=2) if ctx.behavioral else "{}"
    pb_ctx_summary = ctx.pb_context_output.model_dump_json(indent=2) if ctx.pb_context_output else "{}"
    human = (
        f"CS: {ctx.metadata.cs_name} | PB: {ctx.metadata.pb_name}\n\n"
        f"NOTAS POR CRITÉRIO E PILARES:\n{scores_summary}\n\n"
        f"CONTEXTO DO PB:\n{pb_ctx_summary}\n\n"
        + format_transcript_block(ctx.transcript.as_plain_text(), ctx.transcript.raw_summary)
    )
    return model.invoke([("system", system), ("human", human)])
