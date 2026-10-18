import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAnalyses } from "../hooks/useAnalyses";
import { useDashboardStats } from "../hooks/useDashboardStats";
import { useTeamMembers } from "../hooks/useTeamMembers";
import { useUsers } from "../hooks/useUsers";
import { formatDate, formatDurationSeconds } from "../lib/format";
import StatusBadge from "../components/ui/StatusBadge";
import BoardTable from "../components/ui/BoardTable";
import EmptyState from "../components/ui/EmptyState";
import FarolBadge, { toFarolLevel } from "../components/ui/FarolBadge";
import Icon from "../components/ui/Icon";
import { useAuth } from "../context/AuthContext";
import type { AnalysisListItem, AnalysisStatus } from "../types/analysis";

type FilterKey = "todos" | "andamento" | "concluidos" | "falha";

const IN_PROGRESS_STATUSES: AnalysisStatus[] = [
  "CREATED",
  "UPLOADED",
  "TRANSCRIBING",
  "TRANSCRIBED",
  "ANALYZING",
  "GENERATING_REPORTS",
];

function matchesFilter(item: AnalysisListItem, filter: FilterKey): boolean {
  if (filter === "todos") return true;
  if (filter === "concluidos") return item.status === "COMPLETED";
  if (filter === "falha") return item.status === "FAILED";
  return IN_PROGRESS_STATUSES.includes(item.status);
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[parts.length - 1]?.[0] ?? "")).toUpperCase();
}

export default function DashboardPage() {
  const { hasRole } = useAuth();
  const isGestor = hasRole("GESTOR");
  const isAdmin = hasRole("ADMIN");
  const showOwnerColumn = isAdmin || isGestor;
  const gridTemplateColumns = showOwnerColumn
    ? "minmax(0,0.9fr) minmax(0,1.1fr) minmax(0,0.9fr) 90px 84px 240px 176px 20px"
    : "minmax(0,1.3fr) minmax(0,0.9fr) 90px 84px 240px 176px 20px";

  const [searchParams, setSearchParams] = useSearchParams();
  const [filter, setFilter] = useState<FilterKey>("todos");
  const [search, setSearch] = useState("");
  const [ownerFilter, setOwnerFilter] = useState(() => searchParams.get("owner_id") ?? "");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    setOwnerFilter(searchParams.get("owner_id") ?? "");
  }, [searchParams]);

  const team = useTeamMembers();
  const activeUsers = useUsers({ status: "ACTIVE" }, { enabled: isAdmin });
  const colaboradorOptions = isGestor ? (team.data ?? []) : (activeUsers.data ?? []);

  const { data, isLoading, isError } = useAnalyses({
    participant_name: search.trim() || undefined,
    owner_id: ownerFilter || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });
  const { data: stats } = useDashboardStats();

  const visibleItems = useMemo(() => {
    const items = data?.items ?? [];
    return items.filter((i) => matchesFilter(i, filter));
  }, [data, filter]);

  const visibleScoredItems = useMemo(
    () => visibleItems.filter((i) => i.overall_score !== null),
    [visibleItems],
  );

  const statsAvgScore = useMemo(() => {
    if (visibleScoredItems.length === 0) return null;
    const total = visibleScoredItems.reduce((sum, i) => sum + (i.overall_score ?? 0), 0);
    return total / visibleScoredItems.length;
  }, [visibleScoredItems]);

  const statsPredominantFarol = useMemo(() => {
    const withFarol = visibleItems.filter(
      (i): i is AnalysisListItem & { overall_farol_level: string } => i.overall_farol_level !== null,
    );
    if (withFarol.length === 0) return null;
    const countByLevel = new Map<string, number>();
    for (const item of withFarol) {
      const level = item.overall_farol_level;
      countByLevel.set(level, (countByLevel.get(level) ?? 0) + 1);
    }
    let topLevel = withFarol[0].overall_farol_level;
    let topCount = 0;
    for (const [level, count] of countByLevel) {
      if (count > topCount) {
        topLevel = level;
        topCount = count;
      }
    }
    const pct = Math.round((topCount / withFarol.length) * 100);
    return { level: topLevel, pct: `${pct}%` };
  }, [visibleItems]);

  const counts = useMemo(() => {
    const items = data?.items ?? [];
    return {
      todos: items.length,
      andamento: items.filter((i) => matchesFilter(i, "andamento")).length,
      concluidos: items.filter((i) => matchesFilter(i, "concluidos")).length,
      falha: items.filter((i) => matchesFilter(i, "falha")).length,
    };
  }, [data]);

  const hasActiveFilters = Boolean(
    search.trim() || ownerFilter || dateFrom || dateTo || filter !== "todos",
  );

  const clearFilters = () => {
    setSearch("");
    setOwnerFilter("");
    setDateFrom("");
    setDateTo("");
    setFilter("todos");
    if (searchParams.has("owner_id")) {
      const next = new URLSearchParams(searchParams);
      next.delete("owner_id");
      setSearchParams(next);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Análises</h1>
          <span className="page-subtitle">Acompanhe as interações avaliadas e o andamento do processamento.</span>
        </div>
        <Link to="/analyses/new" className="btn btn-primary">
          <Icon name="add" size={20} />
          Nova análise
        </Link>
      </div>

      {data && data.items.length > 0 && (
        <div className="kpi-grid" style={{ margin: "20px 0" }}>
          <div className="kpi-card">
            <span className="kpi-label">{isGestor ? "Análises da equipe" : "Minhas análises"}</span>
            <span className="kpi-value">{visibleItems.length}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">{isGestor ? "Nota média da equipe" : "Minha nota média"}</span>
            <span className="kpi-value">{statsAvgScore !== null ? statsAvgScore.toFixed(1) : "—"}</span>
            <span className="kpi-description">Escala de 0 a 10</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Farol predominante</span>
            <span className="kpi-value" style={{ fontSize: 18 }}>
              {statsPredominantFarol ? (
                <FarolBadge level={toFarolLevel(statsPredominantFarol.level)} />
              ) : (
                "—"
              )}
            </span>
            <span className="kpi-description">{statsPredominantFarol?.pct ?? ""}</span>
          </div>
        </div>
      )}

      {isGestor && stats?.team_board && (
        <div style={{ margin: "20px 0" }}>
          <BoardTable
            title="Quadro da equipe"
            nameColumnLabel="Colaborador"
            rows={stats.team_board.map((row) => ({ id: row.user_id, ...row }))}
            emptyMessage="Nenhum colaborador da equipe com análises concluídas no período."
          />
        </div>
      )}

      {isLoading && <p className="page-subtitle">Carregando...</p>}
      {isError && <p className="error-text">Não foi possível carregar as análises.</p>}

      {!isLoading && data && data.items.length === 0 && !hasActiveFilters && (
        <EmptyState icon="upload_file" title="Nenhuma análise ainda">
          <span className="ui-empty-state-description">
            Envie a transcrição ou a gravação de uma interação comercial para gerar o relatório
            Executivo e o Detalhado.
          </span>
          <Link to="/analyses/new" className="btn btn-primary" style={{ marginTop: 6 }}>
            <Icon name="add" size={20} />
            Criar primeira análise
          </Link>
          <span className="page-subtitle" style={{ fontSize: 12 }}>
            Formatos aceitos: .docx, .txt, .mp3 e .mp4
          </span>
        </EmptyState>
      )}

      {!isLoading && data && (data.items.length > 0 || hasActiveFilters) && (
        <>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", margin: "20px 0" }}>
            <span className="search-field" style={{ width: 220 }}>
              <Icon name="search" size={20} />
              <input
                aria-label="Buscar participante"
                placeholder="Buscar participante"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ border: "none", outline: "none", background: "none", font: "inherit", flex: 1 }}
              />
            </span>
            {showOwnerColumn && (
              <span className="search-field">
                <select
                  aria-label="Filtrar por colaborador"
                  value={ownerFilter}
                  onChange={(e) => setOwnerFilter(e.target.value)}
                  style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
                >
                  <option value="">Todos os colaboradores</option>
                  {colaboradorOptions.map((colaborador) => (
                    <option key={colaborador.id} value={colaborador.id}>
                      {colaborador.name}
                    </option>
                  ))}
                </select>
                <Icon name="expand_more" size={20} />
              </span>
            )}
            <span className="search-field">
              <Icon name="calendar_today" size={18} />
              <input
                type="date"
                aria-label="Data inicial"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
              />
              <span style={{ color: "var(--content-tertiary)" }}>até</span>
              <input
                type="date"
                aria-label="Data final"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(e) => setDateTo(e.target.value)}
                style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
              />
            </span>
            <span style={{ width: 1, height: 24, background: "var(--border-primary)" }} />
            <button className={`pill${filter === "todos" ? " pill-active" : ""}`} onClick={() => setFilter("todos")}>
              Todos <span style={{ opacity: 0.75 }}>{counts.todos}</span>
            </button>
            <button
              className={`pill${filter === "andamento" ? " pill-active" : ""}`}
              onClick={() => setFilter("andamento")}
            >
              Em andamento <span style={{ color: "var(--content-secondary)" }}>{counts.andamento}</span>
            </button>
            <button
              className={`pill${filter === "concluidos" ? " pill-active" : ""}`}
              onClick={() => setFilter("concluidos")}
            >
              Concluídos <span style={{ color: "var(--content-secondary)" }}>{counts.concluidos}</span>
            </button>
            <button className={`pill${filter === "falha" ? " pill-active" : ""}`} onClick={() => setFilter("falha")}>
              Com falha <span style={{ color: "var(--content-secondary)" }}>{counts.falha}</span>
            </button>
            {hasActiveFilters && (
              <button type="button" className="btn btn-secondary" onClick={clearFilters}>
                Limpar filtros
              </button>
            )}
          </div>

          {data.items.length === 0 ? (
            <EmptyState icon="filter_alt_off" title="Nenhuma análise encontrada">
              <span className="ui-empty-state-description">
                Ajuste os filtros de colaborador, participante ou período para ver outros resultados.
              </span>
            </EmptyState>
          ) : (
            <div className="data-table">
              <div className="data-table-row data-table-head" style={{ gridTemplateColumns }}>
                {showOwnerColumn && <span>Colaborador</span>}
                <span>Participante</span>
                <span>Objetivo</span>
                <span>Tempo</span>
                <span>Data</span>
                <span>Nota</span>
                <span>Status</span>
                <span />
              </div>
              {visibleItems.map((item) => (
                <Link
                  key={item.id}
                  to={
                    item.status === "COMPLETED" || item.status === "FAILED"
                      ? `/analyses/${item.id}`
                      : `/analyses/${item.id}/processing`
                  }
                  className="data-table-row"
                  style={{ gridTemplateColumns, color: "inherit", textDecoration: "none" }}
                >
                  {showOwnerColumn && <span>{item.owner_name ?? "—"}</span>}
                  <span className="data-table-participant">
                    <span className="data-table-avatar">{initialsOf(item.participant_name)}</span>
                    <b style={{ fontWeight: 600 }}>{item.participant_name}</b>
                  </span>
                  <span>{item.objective}</span>
                  <span style={{ color: "var(--content-secondary)" }}>
                    {formatDurationSeconds(item.duration_seconds)}
                  </span>
                  <span style={{ color: "var(--content-secondary)" }}>{formatDate(item.created_at)}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {item.overall_farol_level ? (
                      <>
                        <b>{item.overall_score?.toFixed(1) ?? "—"}</b>
                        <FarolBadge level={toFarolLevel(item.overall_farol_level)} />
                      </>
                    ) : (
                      <span style={{ color: "var(--content-secondary)" }}>—</span>
                    )}
                  </span>
                  <StatusBadge status={item.status} />
                  <Icon name="chevron_right" size={20} color="var(--content-secondary)" />
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
