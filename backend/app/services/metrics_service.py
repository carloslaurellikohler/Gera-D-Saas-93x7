"""Orquestração das métricas de evolução (Fase 4) — só leitura. Resolve a janela do
período atual e a janela anterior equivalente (mesma duração, sem overlap), busca as
linhas cruas via MetricsRepository numa única query e agrega em Python."""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.models.user import User, UserRole
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.metrics import (
    CriterionRadarPoint,
    MetricsEvolutionResponse,
    MetricsTrendPoint,
    Period,
)

_PERIOD_DAYS: dict[Period, int] = {"30d": 30, "90d": 90, "6m": 182}

# Ordem fixa de exibição — espelha a ordem canônica de CriterionScore.key no engine,
# para o radar não mudar de orientação entre chamadas por causa da ordem no JSONB.
_CRITERION_ORDER = [
    "posicionamento",
    "conexao",
    "sondagem",
    "direcionamento",
    "encaminhamento",
    "eficiencia_conducao",
]


class MetricsService:
    def __init__(self, repo: MetricsRepository, user_repo: UserRepository) -> None:
        self.repo = repo
        self.user_repo = user_repo

    def get_evolution(self, *, current_user: User, period: Period = "6m") -> MetricsEvolutionResponse:
        days = _PERIOD_DAYS[period]
        today = date.today()
        current_since = today - timedelta(days=days)
        previous_since = current_since - timedelta(days=days)

        if current_user.role == UserRole.ADMIN:
            owner_ids = None
        elif current_user.role == UserRole.GESTOR:
            owner_ids = [u.id for u in self.user_repo.list_subordinates(current_user.id)]
        else:  # COLABORADOR
            owner_ids = [current_user.id]

        rows = self.repo.completed_rows(owner_ids=owner_ids, since=previous_since)
        current_rows = [r for r in rows if _as_date(r.completed_at) >= current_since]
        previous_rows = [r for r in rows if _as_date(r.completed_at) < current_since]

        return MetricsEvolutionResponse(
            period=period,
            radar=_build_radar(current_rows, previous_rows),
            trend=_build_trend(current_rows),
        )


def _build_radar(current_rows, previous_rows) -> list[CriterionRadarPoint]:
    current_scores = _scores_by_criterion(current_rows)
    previous_scores = _scores_by_criterion(previous_rows)
    labels = _labels_by_criterion(current_rows) or _labels_by_criterion(previous_rows)

    points = []
    for key in _CRITERION_ORDER:
        cur, prev = current_scores.get(key, []), previous_scores.get(key, [])
        points.append(
            CriterionRadarPoint(
                key=key,
                label=labels.get(key, key),
                score=_round_or_none(statistics.mean(cur)) if cur else None,
                previous_score=_round_or_none(statistics.mean(prev)) if prev else None,
                sample_size=len(cur),
            )
        )
    return points


def _scores_by_criterion(rows) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for _, result in rows:
        for item in (result or {}).get("scores_by_criterion", []):
            key, score = item.get("key"), item.get("score")
            if key is not None and score is not None:
                out[key].append(score)
    return out


def _labels_by_criterion(rows) -> dict[str, str]:
    out: dict[str, str] = {}
    for _, result in rows:
        for item in (result or {}).get("scores_by_criterion", []):
            key, label = item.get("key"), item.get("label")
            if key and label and key not in out:
                out[key] = label
    return out


def _build_trend(rows) -> list[MetricsTrendPoint]:
    buckets: dict[date, list[dict]] = defaultdict(list)
    for completed_at, result in rows:
        week_start = _as_date(completed_at) - timedelta(days=completed_at.weekday())
        buckets[week_start].append(result or {})

    points = []
    for week_start in sorted(buckets):
        results = buckets[week_start]
        overall = [r["overall_score"] for r in results if r.get("overall_score") is not None]
        p93 = [
            r["pilar_93_score"]["score"]
            for r in results
            if (r.get("pilar_93_score") or {}).get("score") is not None
        ]
        p7 = [
            r["pilar_7_score"]["score"]
            for r in results
            if (r.get("pilar_7_score") or {}).get("score") is not None
        ]
        points.append(
            MetricsTrendPoint(
                period_start=week_start,
                count=len(results),
                avg_overall_score=_round_or_none(statistics.mean(overall)) if overall else None,
                avg_pilar_93=_round_or_none(statistics.mean(p93)) if p93 else None,
                avg_pilar_7=_round_or_none(statistics.mean(p7)) if p7 else None,
            )
        )
    return points


def _round_or_none(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


def _as_date(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value
