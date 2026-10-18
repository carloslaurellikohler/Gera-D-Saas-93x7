"""Orquestração do dashboard agregado (Fase 2) — só leitura, nunca toca engine/storage
(distinto de AnalysisService, que orquestra o pipeline). Resolve o período, delega as
agregações ao DashboardRepository e normaliza o farol via core.farol."""

from __future__ import annotations

import statistics
import uuid
from datetime import date, timedelta

from app.core.farol import get_farol_level
from app.models.user import User, UserRole
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.methodology_repository import MethodologyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.dashboard import (
    DashboardStatsResponse,
    FarolDistributionItem,
    Period,
    TeamBoardRow,
    TrendPoint,
    VolumeByStatus,
)

_PERIOD_DAYS: dict[Period, int] = {"30d": 30, "90d": 90, "6m": 182}

# Diferença mínima de nota entre a primeira e a segunda metade do período para
# considerar a tendência de um grupo como "up"/"down" em vez de "flat" — evita ruído
# de pequenas oscilações entre duas ou três análises.
_TREND_EPSILON = 0.3


class DashboardService:
    def __init__(
        self,
        repo: DashboardRepository,
        methodology_repo: MethodologyRepository,
        user_repo: UserRepository,
    ) -> None:
        self.repo = repo
        self.methodology_repo = methodology_repo
        self.user_repo = user_repo

    def get_stats(self, *, current_user: User, period: Period = "6m") -> DashboardStatsResponse:
        since = date.today() - timedelta(days=_PERIOD_DAYS[period])
        label_color_map = self.methodology_repo.get_label_color_map()

        team_board: list[TeamBoardRow] | None = None

        if current_user.role == UserRole.ADMIN:
            owner_ids = None
            team_board = self._build_team_board(owner_ids, since, label_color_map)
        elif current_user.role == UserRole.GESTOR:
            owner_ids = [u.id for u in self.user_repo.list_subordinates(current_user.id)]
            team_board = self._build_team_board(owner_ids, since, label_color_map)
        else:  # COLABORADOR
            owner_ids = [current_user.id]

        volume = [
            VolumeByStatus(status=status.value, count=count)
            for status, count in self.repo.count_by_status(owner_ids=owner_ids, since=since)
        ]

        band_counts = self.repo.count_by_band_label(owner_ids=owner_ids, since=since)
        total_completed = sum(count for _, count in band_counts)
        farol_distribution = [
            FarolDistributionItem(
                label=label or "Sem classificação",
                level=get_farol_level(label, label_color_map),
                count=count,
                pct=_format_pct(count, total_completed),
            )
            for label, count in band_counts
        ]

        trend = [
            TrendPoint(period_start=period_start, count=count, avg_score=_round_or_none(avg_score))
            for period_start, count, avg_score in self.repo.trend_by_week(owner_ids=owner_ids, since=since)
        ]

        return DashboardStatsResponse(
            period=period,
            volume_by_status=volume,
            farol_distribution=farol_distribution,
            trend=trend,
            team_board=team_board,
        )

    def _build_team_board(
        self, owner_ids: list[uuid.UUID] | None, since: date, label_color_map: dict[str, str]
    ) -> list[TeamBoardRow]:
        if owner_ids is not None and not owner_ids:
            return []
        rows = self.repo.completed_rows_by_owner(owner_ids=owner_ids, since=since)
        groups = _group_entries(rows)
        return [
            TeamBoardRow(
                user_id=str(group_id),
                name=name,
                count=len(entries),
                avg_score=_round_or_none(_avg_score(entries)),
                level=get_farol_level(entries[-1][2], label_color_map),
                trend=_trend_from_entries(entries),
            )
            for group_id, name, entries in groups
        ]


def _group_entries(rows) -> list[tuple]:
    """Agrupa linhas cruas (group_id, name, completed_at, score, band_label) por
    group_id, ordenando cada grupo por completed_at — usado pelo quadro por colaborador
    (ADMIN sem restrição, GESTOR escopado aos subordinados)."""
    groups: dict = {}
    for group_id, name, completed_at, score, band_label in rows:
        group = groups.setdefault(group_id, {"name": name, "entries": []})
        group["name"] = name
        group["entries"].append((completed_at, score, band_label))

    ordered = [
        (group_id, group["name"], sorted(group["entries"], key=lambda e: e[0]))
        for group_id, group in groups.items()
    ]
    ordered.sort(key=lambda item: (_avg_score(item[2]) is None, _avg_score(item[2])))
    return ordered


def _avg_score(entries: list[tuple]) -> float | None:
    scores = [score for _, score, _ in entries if score is not None]
    return statistics.mean(scores) if scores else None


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
