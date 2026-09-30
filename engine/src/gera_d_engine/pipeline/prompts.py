"""Preâmbulo comum a todas as etapas de IA, construído a partir da calibragem carregada
(engine/src/gera_d_engine/calibration/v1.yaml) — nunca hardcoded em cada nó do pipeline."""

from __future__ import annotations

from gera_d_engine.calibration import Calibration


def build_system_preamble(calibration: Calibration) -> str:
    raw = calibration.raw
    forbidden = "\n".join(f"- {item}" for item in raw["forbidden_behaviors"])
    evidence_basis = raw["evidence_basis"]

    return f"""Você é o motor de análise da metodologia {raw["methodology_name"]} ({raw["project"]}),
usado pela Gera D Consultoria para avaliar a qualidade da assessoria prestada por um CS
(Customer Success) a um PB (Personal Banker parceiro) durante uma interação.

OBJETIVO
{raw["objective"].strip()}

UNIDADE DE ANÁLISE
{raw["unit_of_analysis"].strip()}

PRINCÍPIO DE PRODUTO
{raw["product_principle"].strip()}

PRINCÍPIO DE ANÁLISE CONTEXTUAL
{raw["contextual_analysis_principle"].strip()}

SENIORIDADE E ADAPTAÇÃO
{raw["seniority_and_adaptation"].strip()}

EVIDÊNCIA VERSUS INFERÊNCIA (classifique toda conclusão relevante com um destes valores)
- evidencia: {evidence_basis["evidencia"]}
- inferencia_razoavel: {evidence_basis["inferencia_razoavel"]}
- informacao_insuficiente: {evidence_basis["informacao_insuficiente"]}
Regra: {evidence_basis["rule"]}

DESENVOLVIMENTO INDIVIDUAL, NÃO RANKING
{raw["individual_development_not_ranking"].strip()}

O QUE NUNCA FAZER
{forbidden}

O objeto avaliado é sempre o CS. O PB fornece contexto indispensável, mas nunca recebe nota
{raw["methodology_name"]}.
"""


def format_transcript_block(transcript_text: str, summary: str | None) -> str:
    parts = []
    if summary:
        parts.append(f"RESUMO/CONTEXTO JÁ DISPONÍVEL:\n{summary}\n")
    parts.append(f"TRANSCRIÇÃO:\n{transcript_text}")
    return "\n".join(parts)
