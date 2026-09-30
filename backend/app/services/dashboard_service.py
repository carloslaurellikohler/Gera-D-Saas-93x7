"""Orquestração do dashboard agregado (Fase 2) — só leitura, nunca toca engine/storage
(distinto de AnalysisService, que orquestra o pipeline). Resolve o período, delega as
agregações ao DashboardRepository e normaliza o farol via core.farol."""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from app.core.farol import get_farol_level
from app.models.user import User, UserRole
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    DashboardStatsResponse,
    FarolDistributionItem,
    Period,
    ProfessionalBoardRow,
    TrendPoint,
    VolumeByStatus,
)

_PERIOD_DAYS: dict[Period, int] = {"30d": 30, "90d": 90, "6m": 182}

# Diferença mínima de nota entre a primeira e a segunda metade do período para
# considerar a tendência de um PB como "up"/"down" em vez de "flat" — evita ruído de
# pequenas oscilações entre duas ou três análises.
_TREND_EPSILON = 0.3


class DashboardService:
    def __init__(self, repo: DashboardRepository) -> None:
        self.repo = repo

    def get_stats(self, *, current_user: User, period: Period = "6m") -> DashboardStatsResponse:
        since = date.today() - timedelta(days=_PERIOD_DAYS[period])
        is_admin = current_user.role == UserRole.ADMIN
        user_id = None if is_admin else current_user.id

        volume = [
            VolumeByStatus(status=status.value, count=count)
            for status, count in self.repo.count_by_status(user_id=user_id, since=since)
        ]

        band_counts = self.repo.count_by_band_label(user_id=user_id, since=since)
        total_completed = sum(count for _, count in band_counts)
        farol_distribution = [
            FarolDistributionItem(
                label=label or "Sem classificação",
                level=get_farol_level(label),
                count=count,
                pct=_format_pct(count, total_completed),
            )
            for label, count in band_counts
        ]

        trend = [
            TrendPoint(period_start=period_start, count=count, avg_score=_round_or_none(avg_score))
            for period_start, count, avg_score in self.repo.trend_by_week(user_id=user_id, since=since)
        ]

        board = self._build_board(since) if is_admin else None

        return DashboardStatsResponse(
            period=period,
            volume_by_status=volume,
            farol_distribution=farol_distribution,
            trend=trend,
            board=board,
        )

    def _build_board(self, since: date) -> list[ProfessionalBoardRow]:
        rows = self.repo.completed_rows_by_participant(since=since)

        groups: dict[str, dict] = {}
        for pb_id, participant_name, completed_at, score, band_label in rows:
            group = groups.setdefault(
                pb_id, {"name": participant_name, "entries": [], "pb_id_source": pb_id}
            )
            group["name"] = participant_name
            group["entries"].append((completed_at, score, band_label))

        board: list[ProfessionalBoardRow] = []
        for pb_id, group in groups.items():
            entries = sorted(group["entries"], key=lambda e: e[0])
            scores = [score for _, score, _ in entries if score is not None]
            avg_score = statistics.mean(scores) if scores else None
            latest_label = entries[-1][2]

            board.append(
                ProfessionalBoardRow(
                    pb_id=pb_id,
                    name=group["name"],
                    count=len(entries),
                    avg_score=_round_or_none(avg_score),
                    level=get_farol_level(latest_label),
                    trend=_trend_from_entries(entries),
                )
            )

        board.sort(key=lambda row: (row.avg_score is None, row.avg_score))
        return board


def _format_pct(count: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{round(count / total * 100)}%"


def _round_or_none(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


def _trend_from_entries(entries: list[tuple]) -> str | None:
    """Compara a média da primeira metade das análises (por completed_at) com a
    segunda metade, dentro do próprio período consultado — evita uma segunda query
    comparando com o período anterior, mantendo o repositório simples."""
    scored = [score for _, score, _ in entries if score is not None]
    if len(scored) < 2:
        return None
    midpoint = len(scored) // 2
    older_avg = statistics.mean(scored[:midpoint]) if midpoint else scored[0]
    newer_avg = statistics.mean(scored[midpoint:])
    delta = newer_avg - older_avg
    if delta > _TREND_EPSILON:
        return "up"
    if delta < -_TREND_EPSILON:
        return "down"
    return "flat"
