"""Normalização do farol de uma análise para a UI. `overall_band_label` (engine,
analysis_result JSONB) é a fonte de verdade da classificação — este módulo só traduz o
texto livre da engine para a chave (`FarolLevel`) que o frontend já usa em FarolBadge,
para que backend e frontend nunca recalculem banding por conta própria a partir do
overall_score (ver ROADMAP.md: nota geral vem do julgamento holístico da engine)."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

FarolLevel = str  # "excelente" | "atencao" | "prioritario" | "critico" | "outro"

# Espelha os labels de engine/src/gera_d_engine/calibration/v1.yaml::score_bands.
# Se a calibração mudar o texto do label, o mapeamento cai no fallback "outro" (ver
# get_farol_level) em vez de quebrar — mas a distribuição de farol do dashboard passa a
# não reconhecer o novo label até este dicionário ser atualizado.
FAROL_LABEL_TO_LEVEL: dict[str, FarolLevel] = {
    "Excelente desempenho": "excelente",
    "Atenção": "atencao",
    "Desenvolvimento prioritário": "prioritario",
    "Desenvolvimento crítico": "critico",
}

_FALLBACK_LEVEL: FarolLevel = "outro"


def get_farol_level(band_label: str | None) -> FarolLevel:
    if band_label is None:
        return _FALLBACK_LEVEL
    level = FAROL_LABEL_TO_LEVEL.get(band_label)
    if level is None:
        log.warning("overall_band_label desconhecido, sem mapeamento de farol: %r", band_label)
        return _FALLBACK_LEVEL
    return level
