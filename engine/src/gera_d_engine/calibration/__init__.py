"""Carregamento da calibragem (critérios, régua de notas, regras) — seção 26 da especificação."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from gera_d_engine.config import DEFAULT_CALIBRATION_FILE


@dataclass(frozen=True)
class ScoreBand:
    key: str
    label: str
    color: str
    min: float
    max: float


@dataclass(frozen=True)
class Calibration:
    raw: dict[str, Any]
    score_bands: list[ScoreBand] = field(default_factory=list)

    @property
    def calibration_version(self) -> str:
        return self.raw["calibration_version"]

    @property
    def criteria(self) -> dict[str, Any]:
        return self.raw["criteria"]

    def criterion_label(self, key: str) -> str:
        return self.criteria[key]["label"]

    def classify_band(self, score: float) -> ScoreBand:
        for band in self.score_bands:
            if band.min <= score <= band.max:
                return band
        # Fallback defensivo: nunca deve ocorrer se o score estiver em [0, 10].
        return self.score_bands[-1]

    def format_score_line(self, score: float, criterion_label: str) -> str:
        template = self.raw.get("score_format", "● {nota} | {criterio}")
        return template.format(nota=f"{score:.1f}".replace(".", ","), criterio=criterion_label.upper())


@lru_cache(maxsize=4)
def load_calibration(path: str | Path = DEFAULT_CALIBRATION_FILE) -> Calibration:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    bands = [
        ScoreBand(
            key=b["key"],
            label=b["label"],
            color=b["color"],
            min=float(b["min"]),
            max=float(b["max"]),
        )
        for b in raw["score_bands"]
    ]
    return Calibration(raw=raw, score_bands=bands)
