import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAnalyses } from "../hooks/useAnalyses";
import { formatDate } from "../lib/format";
import StatusBadge from "../components/ui/StatusBadge";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
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
  const { data, isLoading, isError } = useAnalyses();
  const [filter, setFilter] = useState<FilterKey>("todos");
  const [search, setSearch] = useState("");

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
