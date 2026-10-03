"""Única ponte entre Methodology (Postgres, Fase 7) e o shape Calibration esperado por
gera_d_engine. Sempre que um novo campo global for lido por pipeline/prompts.py ou
pipeline/nodes/*.py, ele precisa existir em Methodology.content com a mesma chave — não
há validação de schema formal aqui (ver MethodologyService.publish() para as validações
de publish-time que existem)."""

from __future__ import annotations

from gera_d_engine.calibration import Calibration, ScoreBand

from app.models.methodology import Methodology


def build_calibration(methodology: Methodology) -> Calibration:
    criteria: dict[str, dict] = {}
    for category in sorted(methodology.categories, key=lambda c: c.order_index):
        criteria[category.key] = {
            "label": category.label,
            "description": category.description,
            **category.extra,
        }

    score_bands_raw = [
        {
            "min": calibrator.min,
            "max": calibrator.max,
            "key": calibrator.key,
            "label": calibrator.label,
            "color": calibrator.color.value,
        }
        for calibrator in sorted(methodology.calibrators, key=lambda c: c.order_index)
    ]

    raw = {
        **methodology.content,
        "calibration_version": methodology.calibration_version,
        "methodology_name": methodology.methodology_name,
        "project": methodology.project,
        "criteria": criteria,
        "score_bands": score_bands_raw,
    }

    bands = [
        ScoreBand(
            key=band["key"],
            label=band["label"],
            color=band["color"],
            min=float(band["min"]),
            max=float(band["max"]),
        )
        for band in score_bands_raw
    ]
    return Calibration(raw=raw, score_bands=bands)
