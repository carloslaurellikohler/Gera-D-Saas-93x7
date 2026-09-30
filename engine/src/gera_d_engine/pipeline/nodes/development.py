"""Etapa 7 — Desenvolvimento: síntese narrativa, pontos preservados, riscos, oportunidades
perdidas, perguntas sugeridas e recomendação executiva (seções 6, 16 e 17)."""

from __future__ import annotations

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble, format_transcript_block
from gera_d_engine.schemas.steps import DevelopmentOutput


def run(ctx: PipelineContext) -> DevelopmentOutput:
    raw = ctx.calibration.raw
    model = build_chat_model(ctx.settings).with_structured_output(DevelopmentOutput)

    taxonomy = raw["development_taxonomy"]
    questions_examples = "\n".join(f"- {q}" for q in raw["suggested_questions_examples"])
    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: DESENVOLVIMENTO\n"
        "Escreva `executive_diagnosis` (2-3 frases, para a Visão Executiva) e `general_reading` "
        "(1-2 parágrafos, para a Visão Detalhada), sintetizando como o CS conduziu a interação e "
        "o que isso significou para o PB. Escreva também `overall_classification_text`: uma frase "
        'curta no estilo "Atenção: boa base relacional e técnica, com baixa conversão do potencial '
        'em plano de ativação", combinando a faixa de classificação com o diagnóstico central.\n\n'
        f"- pontos_preservados: {taxonomy['pontos_preservados']}\n"
        f"- riscos: {taxonomy['riscos']}\n"
        f"- oportunidades_perdidas: {taxonomy['oportunidades_perdidas']}\n\n"
        f"{raw['suggested_questions_rule'].strip()} Gere perguntas contextuais (não script fixo), "
        f"no espírito destes exemplos (não copie literalmente, adapte ao caso):\n{questions_examples}\n\n"
        f"RECOMENDAÇÃO EXECUTIVA: {raw['executive_recommendation_rule'].strip()}"
    )

    behavioral_summary = ctx.behavioral.model_dump_json(indent=2) if ctx.behavioral else "{}"
    consequence_summary = ctx.consequence.model_dump_json(indent=2) if ctx.consequence else "{}"
    pb_ctx_summary = ctx.pb_context_output.model_dump_json(indent=2) if ctx.pb_context_output else "{}"
    human = (
        f"CS: {ctx.metadata.cs_name} | PB: {ctx.metadata.pb_name}\n\n"
        f"NOTAS POR CRITÉRIO E PILARES:\n{behavioral_summary}\n\n"
        f"ANÁLISE DE CONSEQUÊNCIA:\n{consequence_summary}\n\n"
        f"CONTEXTO DO PB:\n{pb_ctx_summary}\n\n"
        + format_transcript_block(ctx.transcript.as_plain_text(), ctx.transcript.raw_summary)
    )
    return model.invoke([("system", system), ("human", human)])
