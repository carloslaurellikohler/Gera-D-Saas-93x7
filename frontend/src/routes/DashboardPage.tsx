import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAnalyses } from "../hooks/useAnalyses";
import { useDashboardStats } from "../hooks/useDashboardStats";
import { formatDate } from "../lib/format";
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
  const { data, isLoading, isError } = useAnalyses();
  const { data: stats } = useDashboardStats();
  const [filter, setFilter] = useState<FilterKey>("todos");
  const [search, setSearch] = useState("");

  const statsTotalVolume = useMemo(
    () => stats?.volume_by_status.reduce((sum, v) => sum + v.count, 0) ?? 0,
    [stats],
  );

  const statsAvgScore = useMemo(() => {
    if (!stats) return null;
    const scored = stats.trend.filter((t) => t.avg_score !== null);
    const totalCount = scored.reduce((sum, t) => sum + t.count, 0);
    if (totalCount === 0) return null;
    const weighted = scored.reduce((sum, t) => sum + (t.avg_score ?? 0) * t.count, 0);
    return weighted / totalCount;
  }, [stats]);

  const statsPredominantFarol = useMemo(() => {
    if (!stats || stats.farol_distribution.length === 0) return null;
    return stats.farol_distribution.reduce((max, item) => (item.count > max.count ? item : max));
  }, [stats]);

  const counts = useMemo(() => {
    const items = data?.items ?? [];
    return {
      todos: items.length,
      andamento: items.filter((i) => matchesFilter(i, "andamento")).length,
      concluidos: items.filter((i) => matchesFilter(i, "concluidos")).length,
      falha: items.filter((i) => matchesFilter(i, "falha")).length,
    };
  }, [data]);

  const visibleItems = useMemo(() => {
    const items = data?.items ?? [];
    return items
      .filter((i) => matchesFilter(i, filter))
      .filter((i) => i.participant_name.toLowerCase().includes(search.trim().toLowerCase()));
  }, [data, filter, search]);

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

      {stats && statsTotalVolume > 0 && (
        <div className="kpi-grid" style={{ margin: "20px 0" }}>
          <div className="kpi-card">
            <span className="kpi-label">{isGestor ? "Análises da equipe" : "Minhas análises"}</span>
            <span className="kpi-value">{statsTotalVolume}</span>
            <span className="kpi-description">Últimos 6 meses</span>
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

      {!isLoading && data && data.items.length === 0 && (
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

      {!isLoading && data && data.items.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", margin: "20px 0" }}>
            <span className="search-field" style={{ width: 260 }}>
              <Icon name="search" size={20} />
              <input
                aria-label="Buscar participante"
                placeholder="Buscar participante"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ border: "none", outline: "none", background: "none", font: "inherit", flex: 1 }}
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
          </div>

          <div className="data-table">
            <div
              className="data-table-row data-table-head"
              style={{ gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1fr) 84px 176px 20px" }}
            >
              <span>Participante</span>
              <span>Objetivo</span>
              <span>Data</span>
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
                style={{
                  gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1fr) 84px 176px 20px",
                  color: "inherit",
                  textDecoration: "none",
                }}
              >
                <span className="data-table-participant">
                  <span className="data-table-avatar">{initialsOf(item.participant_name)}</span>
                  <b style={{ fontWeight: 600 }}>{item.participant_name}</b>
                </span>
                <span>{item.objective}</span>
                <span style={{ color: "var(--content-secondary)" }}>{formatDate(item.created_at)}</span>
                <StatusBadge status={item.status} />
                <Icon name="chevron_right" size={20} color="var(--content-secondary)" />
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
