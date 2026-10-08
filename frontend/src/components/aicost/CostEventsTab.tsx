import { useState } from "react";
import { useAiCostEvents } from "../../hooks/useAiCostEvents";
import { formatDateTime, formatUsd } from "../../lib/format";
import type { AiCostFeature, AiCostOperation, AiCostPeriod, AiCostStatus } from "../../types/aiCost";
import EmptyState from "../ui/EmptyState";
import Icon from "../ui/Icon";

const PAGE_SIZE = 50;

const FEATURE_FILTERS: { key: AiCostFeature | "all"; label: string }[] = [
  { key: "all", label: "Todas as origens" },
  { key: "ANALYSIS", label: "Análises" },
  { key: "ASSISTANT", label: "Assistente" },
  { key: "INGESTION", label: "Ingestão" },
];

const OPERATION_FILTERS: { key: AiCostOperation | "all"; label: string }[] = [
  { key: "all", label: "Todas as operações" },
  { key: "CHAT", label: "Chat" },
  { key: "TRANSCRIPTION", label: "Transcrição" },
  { key: "EMBEDDING", label: "Embedding" },
];

// Mostra por que uma linha não tem custo apurado — a tela não esconde subcontagem.
const STATUS_HINT: Record<AiCostStatus, string | null> = {
  PRICED: null,
  NO_PRICE: "sem preço",
  NO_UNITS: "sem medição",
};

const COLUMNS = "160px 110px 110px minmax(0, 1.1fr) minmax(0, 1fr) minmax(0, 1fr) 110px 110px";

export default function CostEventsTab({ period }: { period: AiCostPeriod }) {
  const [feature, setFeature] = useState<AiCostFeature | "all">("all");
  const [operation, setOperation] = useState<AiCostOperation | "all">("all");
  const [model, setModel] = useState<string>("all");
  const [offset, setOffset] = useState(0);

  const events = useAiCostEvents({
    period,
    feature: feature === "all" ? undefined : feature,
    operation: operation === "all" ? undefined : operation,
    model: model === "all" ? undefined : model,
    offset,
    limit: PAGE_SIZE,
  });

  const data = events.data;
  const page = data ? Math.floor(data.offset / PAGE_SIZE) + 1 : 1;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const resetTo = (updater: () => void) => {
    updater();
    setOffset(0);
  };

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
        <span className="search-field">
          <select
            aria-label="Origem"
            value={feature}
            onChange={(e) => resetTo(() => setFeature(e.target.value as AiCostFeature | "all"))}
            style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
          >
            {FEATURE_FILTERS.map((f) => (
              <option key={f.key} value={f.key}>
                {f.label}
              </option>
            ))}
          </select>
          <Icon name="expand_more" size={20} />
        </span>
        <span className="search-field">
          <select
            aria-label="Operação"
            value={operation}
            onChange={(e) =>
              resetTo(() => setOperation(e.target.value as AiCostOperation | "all"))
            }
            style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
          >
            {OPERATION_FILTERS.map((f) => (
              <option key={f.key} value={f.key}>
                {f.label}
              </option>
            ))}
          </select>
          <Icon name="expand_more" size={20} />
        </span>
        <span className="search-field">
          <select
            aria-label="Modelo"
            value={model}
            onChange={(e) => resetTo(() => setModel(e.target.value))}
            style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
          >
            <option value="all">Todos os modelos</option>
            {(data?.models ?? []).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <Icon name="expand_more" size={20} />
        </span>
      </div>

      {events.isLoading && <p className="page-subtitle">Carregando...</p>}
      {events.isError && (
        <p className="error-text">Não foi possível carregar os eventos de consumo.</p>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          icon="data_usage"
          title="Nenhuma chamada registrada"
          description="Nenhum consumo de IA corresponde aos filtros selecionados neste período."
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="data-table">
            <div className="data-table-row data-table-head" style={{ gridTemplateColumns: COLUMNS }}>
              <span>Data e hora</span>
              <span>Origem</span>
              <span>Operação</span>
              <span>Etapa</span>
              <span>Modelo</span>
              <span>Usuário</span>
              <span style={{ textAlign: "right" }}>Tokens</span>
              <span style={{ textAlign: "right" }}>Custo</span>
            </div>
            {data.items.map((event) => {
              const hint = STATUS_HINT[event.cost_status];
              return (
                <div
                  key={event.id}
                  className="data-table-row"
                  style={{ gridTemplateColumns: COLUMNS }}
                >
                  <span style={{ fontSize: 13 }}>{formatDateTime(event.occurred_at)}</span>
                  <span style={{ fontSize: 13 }}>{event.feature}</span>
                  <span style={{ fontSize: 13 }}>{event.operation}</span>
                  <span style={{ fontSize: 13 }}>
                    {event.stage_label}
                    {event.attempt > 0 && (
                      <span style={{ color: "var(--content-negative)" }}>
                        {" "}
                        · {event.attempt + 1}ª tentativa
                      </span>
                    )}
                  </span>
                  <span style={{ fontSize: 13 }}>{event.model}</span>
                  <span style={{ fontSize: 13, color: "var(--content-secondary)" }}>
                    {event.user_name ?? "—"}
                  </span>
                  <span style={{ textAlign: "right", fontSize: 13 }}>
                    {event.operation === "TRANSCRIPTION"
                      ? event.audio_seconds !== null
                        ? `${(event.audio_seconds / 60).toFixed(1)} min`
                        : "—"
                      : `${event.input_tokens} / ${event.output_tokens}`}
                  </span>
                  <span style={{ textAlign: "right" }}>
                    {formatUsd(event.cost_usd)}
                    {hint && (
                      <span
                        className="pill"
                        style={{ marginLeft: 6, fontSize: 11, padding: "1px 6px" }}
                        title={
                          event.error_type
                            ? `A chamada falhou (${event.error_type})`
                            : "Esta chamada não entrou no total"
                        }
                      >
                        {hint}
                      </span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 14,
            }}
          >
            <span className="page-subtitle">
              {data.total} {data.total === 1 ? "chamada" : "chamadas"} no período · página {page} de{" "}
              {totalPages}
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                Anterior
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Próxima
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
