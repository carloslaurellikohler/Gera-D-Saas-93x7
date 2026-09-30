"""Prepara os dados do AnalysisResult para os templates Jinja2, aplicando a régua de faixas
(classify_band) fora do template — templates ficam só com apresentação, sem lógica de negócio."""

from __future__ import annotations

from gera_d_engine.calibration import Calibration
from gera_d_engine.schemas.analysis import AnalysisResult


def _fmt_score(score: float) -> str:
    return f"{score:.1f}".replace(".", ",")


def _score_view(score: float, label: str, calibration: Calibration) -> dict:
    band = calibration.classify_band(score)
    return {
        "score": _fmt_score(score),
        "label": label,
        "band_key": band.key,
        "band_label": band.label,
    }


def build_view(result: AnalysisResult, calibration: Calibration) -> dict:
    criteria_view = [
        {
            **_score_view(c.score, c.label, calibration),
            "reading": c.reading,
            "analysis": c.analysis,
            "evidences": [e.model_dump() for e in c.evidences],
        }
        for c in result.scores_by_criterion
    ]

    pilar_93 = _score_view(result.pilar_93_score.score, result.pilar_93_score.label, calibration)
    pilar_93["analysis"] = result.pilar_93_score.analysis
    pilar_7 = _score_view(result.pilar_7_score.score, result.pilar_7_score.label, calibration)
    pilar_7["analysis"] = result.pilar_7_score.analysis
    overall = _score_view(result.overall_score, "Avaliação final", calibration)

    potential_key_map = {"Baixo": "baixo", "Médio": "medio", "Médio-alto": "medio", "Alto": "alto"}

    return {
        "r": result,
        "criteria": criteria_view,
        "pilar_93": pilar_93,
        "pilar_7": pilar_7,
        "overall": overall,
        "computed_average": _fmt_score(result.computed_average),
        "result_potential_key": potential_key_map.get(result.result_potential.level, "medio"),
        "pb_potential_key": {"Baixo": "baixo", "Médio": "medio", "Alto": "alto"}.get(
            result.pb_commercial_potential.level, "medio"
        ),
    }
