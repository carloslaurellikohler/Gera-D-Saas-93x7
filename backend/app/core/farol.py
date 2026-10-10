"""Normalização do farol de uma análise para a UI. `overall_band_label` (engine,
analysis_result JSONB) é a fonte de verdade da classificação — este módulo só traduz o
texto livre da engine para a chave (`FarolLevel`) que o frontend já usa em FarolBadge,
para que backend e frontend nunca recalculem banding por conta própria a partir do
overall_score (nota geral vem do julgamento holístico da engine, nunca de fórmula).

Desde a Fase 7, o mapeamento label -> cor vem do Postgres (MethodologyRepository.
get_label_color_map(), que cobre todas as versões já publicadas/arquivadas — uma
análise antiga pode referenciar o label de uma versão já encerrada). cor -> nível de
UI continua fixo aqui: é vocabulário do design system (4 faixas de farol), não da
metodologia."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

FarolLevel = str  # "excelente" | "atencao" | "prioritario" | "critico" | "outro"

_COLOR_TO_LEVEL: dict[str, FarolLevel] = {
    "verde": "excelente",
    "amarelo": "atencao",
    "laranja": "prioritario",
    "vermelho": "critico",
}

_FALLBACK_LEVEL: FarolLevel = "outro"


def get_farol_level(band_label: str | None, label_color_map: dict[str, str]) -> FarolLevel:
    if band_label is None:
        return _FALLBACK_LEVEL
    color = label_color_map.get(band_label)
    if color is None:
        log.warning("overall_band_label sem Calibrator correspondente no Postgres: %r", band_label)
        return _FALLBACK_LEVEL
    level = _COLOR_TO_LEVEL.get(color)
    if level is None:
        log.warning("Calibrator com cor desconhecida para o label %r: %r", band_label, color)
        return _FALLBACK_LEVEL
    return level
