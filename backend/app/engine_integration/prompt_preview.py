"""Renderiza o system prompt que a engine receberá para uma versão de metodologia.

Existe para fechar o laço de edição da tela /calibracao: o ADMIN escreve âncoras,
exemplos e regras de elegibilidade em formulários, e o calibration_builder os compila
num texto que, até a Fase 9, só era observável rodando uma análise de verdade. Aqui a
engine é usada como biblioteca de formatação — reusa build_system_preamble e a mesma
função de formatação de critérios do nó de análise comportamental, para que a prévia
nunca divirja do prompt real por duplicação de código.

`_format_criteria` é privada na engine; importá-la é deliberado — reimplementá-la aqui
criaria exatamente a divergência silenciosa que esta tela existe para evitar."""

from __future__ import annotations

from gera_d_engine.pipeline.nodes.behavioral_analysis import _format_criteria
from gera_d_engine.pipeline.prompts import build_system_preamble

from app.engine_integration.calibration_builder import build_calibration
from app.models.methodology import Methodology


def build_prompt_preview(methodology: Methodology) -> dict:
    """Levanta KeyError quando `content` não tem alguma chave que o preâmbulo lê — o
    caso de uma versão anterior à validação de MethodologyContentIn. A rota traduz."""
    calibration = build_calibration(methodology)
    return {
        "calibration_version": calibration.calibration_version,
        "system_preamble": build_system_preamble(calibration),
        "criteria_block": _format_criteria(calibration.raw),
    }
