"""Etapa 5 — Análise comportamental do CS: os 6 critérios e os Pilares 93/7 (seções 2 e 5-9)."""

from __future__ import annotations

from gera_d_engine.pipeline.context import PipelineContext
from gera_d_engine.pipeline.llm import build_chat_model
from gera_d_engine.pipeline.prompts import build_system_preamble, format_transcript_block
from gera_d_engine.schemas.steps import BehavioralAnalysisOutput


def _format_criteria(calibration_raw: dict) -> str:
    blocks = []
    for key, crit in calibration_raw["criteria"].items():
        lines = [f"### {crit['label']} (key=\"{key}\")", crit["description"].strip()]
        for extra_key in ("good_performance", "risks", "calibration_note", "critical_rule", "cross_impact"):
            if extra_key in crit:
                lines.append(f"{extra_key}: {crit[extra_key].strip()}")
        if "desired_structure" in crit:
            lines.append(f"Estrutura desejável: {crit['desired_structure']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _format_bands(calibration_raw: dict) -> str:
    return "\n".join(
        f"- {b['min']:.1f} a {b['max']:.1f}: {b['label']}" for b in calibration_raw["score_bands"]
    )


def run(ctx: PipelineContext) -> BehavioralAnalysisOutput:
    raw = ctx.calibration.raw
    model = build_chat_model(ctx.settings).with_structured_output(BehavioralAnalysisOutput)

    system = build_system_preamble(ctx.calibration) + (
        "\n\nTAREFA: ANÁLISE COMPORTAMENTAL DO CS\n"
        "Avalie o CS nos 6 critérios abaixo. Para cada critério, dê uma nota de 0 a 10 (uma casa "
        "decimal), uma leitura curta (uma frase, para dashboard) e uma análise detalhada (um "
        "parágrafo), sempre apoiadas em evidências estruturadas "
        f"({raw['evidence_structure']}), cada uma com seu `basis` (evidência/inferência/"
        "informação insuficiente).\n\n"
        f"CRITÉRIOS:\n{_format_criteria(raw)}\n\n"
        f"REGRA DOS PILARES: {raw['pillars']['rule'].strip()}\n"
        f"- {raw['pillars']['pilar_93']['label']}: {raw['pillars']['pilar_93']['description'].strip()}\n"
        f"- {raw['pillars']['pilar_7']['label']}: {raw['pillars']['pilar_7']['description'].strip()}\n\n"
        f"RÉGUA DE NOTAS (referência para a leitura, não determina o texto):\n{_format_bands(raw)}\n"
    )

    fact_summary = ctx.fact_extraction.model_dump_json(indent=2) if ctx.fact_extraction else "{}"
    pb_ctx_summary = ctx.pb_context_output.model_dump_json(indent=2) if ctx.pb_context_output else "{}"
    human = (
        f"CS: {ctx.metadata.cs_name} | PB: {ctx.metadata.pb_name} | "
        f"Tipo de interação: {ctx.metadata.interaction_type}\n\n"
        f"FATOS EXTRAÍDOS:\n{fact_summary}\n\n"
        f"CONTEXTO DO PB:\n{pb_ctx_summary}\n\n"
        + format_transcript_block(ctx.transcript.as_plain_text(), ctx.transcript.raw_summary)
    )
    return model.invoke([("system", system), ("human", human)])
