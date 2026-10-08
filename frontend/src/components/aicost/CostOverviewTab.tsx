import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBrlFromUsd, formatDate, formatDateTime, formatTokens, formatUsd } from "../../lib/format";
import type { AiCostSummary } from "../../types/aiCost";
import EmptyState from "../ui/EmptyState";
import Icon from "../ui/Icon";
import ProgressBar from "../ui/ProgressBar";

// Paleta categórica dos tokens de styles/tokens/colors.css. Deliberadamente não usa
// --gerad-navy, que no resto do produto já significa "nota média": custo precisa ler como
// outra grandeza.
const OPERATION_COLORS: Record<string, string> = {
  CHAT: "var(--blue-2)",
  TRANSCRIPTION: "var(--orange-2)",
  EMBEDDING: "var(--green-3)",
};

const BUDGET_COLORS: Record<string, string> = {
  unset: "var(--content-secondary)",
  ok: "var(--content-positive)",
  warn: "var(--content-alert)",
  over: "var(--content-negative)",
};

export default function CostOverviewTab({
  summary,
  onGoToPrices,
}: {
  summary: AiCostSummary;
  onGoToPrices: () => void;
}) {
  const { kpis, budget, usd_to_brl_rate: rate } = summary;

  const trendData = useMemo(
    () =>
      summary.trend_by_feature.map((point) => ({
        periodo: formatDate(point.period_start),
        Análises: point.analysis_usd,
        Assistente: point.assistant_usd,
        Ingestão: point.ingestion_usd,
      })),
    [summary.trend_by_feature],
  );

  const operationData = useMemo(
    () =>
      summary.by_operation
        .filter((item) => item.total_usd > 0)
        .map((item) => ({ name: item.label, value: item.total_usd, key: item.key })),
    [summary.by_operation],
  );

  const stageData = useMemo(
    () =>
      summary.by_stage
        .filter((item) => item.total_usd > 0)
        .map((item) => ({ etapa: item.label, custo: item.total_usd })),
    [summary.by_stage],
  );

  const maxModelCost = Math.max(...summary.by_model.map((m) => m.total_usd), 0);

  return (
    <>
      {summary.has_placeholder_prices && (
        <div className="info-banner" style={{ marginTop: 20 }}>
          <Icon name="price_change" size={20} />
          <span>
            Há preços marcados como estimados em vigor. Confirme os valores para que o total
            seja confiável.{" "}
            <button
              type="button"
              className="link-button"
              onClick={onGoToPrices}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                font: "inherit",
                color: "var(--content-link)",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Ver preços
            </button>
          </span>
        </div>
      )}

      {kpis.unpriced_events > 0 && (
        <div
          className="info-banner"
          style={{ marginTop: 16, background: "var(--background-alert-n2)" }}
        >
          <Icon name="warning" size={20} />
          <span>
            <strong>{kpis.unpriced_events}</strong>{" "}
            {kpis.unpriced_events === 1 ? "chamada" : "chamadas"} sem preço cadastrado neste
            período — o total abaixo está <strong>subestimado</strong>. Cadastre o preço do
            modelo para custear essas chamadas.{" "}
            <button
              type="button"
              onClick={onGoToPrices}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                font: "inherit",
                color: "var(--content-link)",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Cadastrar preço
            </button>
          </span>
        </div>
      )}

      <div className="kpi-grid" style={{ margin: "24px 0" }}>
        <div className="kpi-card">
          <span className="kpi-label">Custo total no período</span>
          <span className="kpi-value">{formatUsd(kpis.total_usd)}</span>
          <span className="kpi-description">
            {formatBrlFromUsd(kpis.total_usd, rate) ?? `${kpis.events} chamadas à OpenAI`}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Custo médio por análise</span>
          <span className="kpi-value">{formatUsd(kpis.avg_usd_per_analysis)}</span>
          <span className="kpi-description">
            {kpis.analyses_with_cost} {kpis.analyses_with_cost === 1 ? "análise" : "análises"} no
            período
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Custo do assistente</span>
          <span className="kpi-value">{formatUsd(kpis.avg_usd_per_assistant_message)}</span>
          <span className="kpi-description">
            por mensagem · {kpis.assistant_messages} no período
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Custo de retentativas</span>
          <span
            className="kpi-value"
            style={{ color: kpis.retry_usd > 0 ? "var(--content-negative)" : undefined }}
          >
            {formatUsd(kpis.retry_usd)}
          </span>
          <span className="kpi-description">
            {kpis.retry_events} {kpis.retry_events === 1 ? "chamada reexecutada" : "chamadas reexecutadas"}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Tokens</span>
          <span className="kpi-value" style={{ fontSize: 22 }}>
            {formatTokens(kpis.input_tokens)} ⇢ {formatTokens(kpis.output_tokens)}
          </span>
          <span className="kpi-description">
            entrada ⇢ saída
            {kpis.cached_input_tokens > 0 && ` · ${formatTokens(kpis.cached_input_tokens)} em cache`}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Áudio transcrito</span>
          <span className="kpi-value">{kpis.audio_minutes.toFixed(0)} min</span>
          <span className="kpi-description">faturado por minuto pelo Whisper</span>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 12,
          }}
        >
          <h3>Orçamento do mês</h3>
          <span className="page-subtitle" style={{ fontSize: 12 }}>
            Apenas informativo — nunca bloqueia análises
          </span>
        </div>
        {budget.status === "unset" ? (
          <EmptyState
            icon="savings"
            title="Nenhuma meta definida para este mês"
            description={`Já foram gastos ${formatUsd(budget.spent_usd)} no mês. Defina uma meta para acompanhar o consumo.`}
          >
            <button type="button" className="btn btn-primary" onClick={onGoToPrices}>
              Definir meta
            </button>
          </EmptyState>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 8,
              }}
            >
              <strong style={{ fontSize: 20, color: BUDGET_COLORS[budget.status] }}>
                {formatUsd(budget.spent_usd)}
              </strong>
              <span className="page-subtitle">
                de {formatUsd(budget.amount_usd)} ({budget.pct?.toFixed(0)}%)
              </span>
            </div>
            <ProgressBar percent={budget.pct ?? 0} />
            <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 13 }}>
              {budget.projected_month_end_usd !== null && (
                <span className="page-subtitle">
                  Projeção de fim de mês: {formatUsd(budget.projected_month_end_usd)}
                </span>
              )}
              {budget.status === "over" && (
                <span style={{ color: "var(--content-negative)", fontWeight: 500 }}>
                  Meta do mês estourada
                </span>
              )}
              {budget.status === "warn" && (
                <span style={{ color: "var(--content-alert-dark, var(--content-alert))", fontWeight: 500 }}>
                  Acima de {budget.warn_threshold_pct}% da meta
                </span>
              )}
            </div>
          </>
        )}
      </div>

      <div className="two-col-grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Custo por período e origem</h3>
          {trendData.length === 0 ? (
            <p className="page-subtitle">Sem consumo registrado no período.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                <XAxis dataKey="periodo" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip formatter={(value) => formatUsd(typeof value === "number" ? value : null)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Análises" stackId="custo" fill="var(--blue-2)" />
                <Bar dataKey="Assistente" stackId="custo" fill="var(--purple-2)" />
                <Bar dataKey="Ingestão" stackId="custo" fill="var(--teal-3)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Custo por tipo de operação</h3>
          {operationData.length === 0 ? (
            <p className="page-subtitle">Sem consumo registrado no período.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={operationData} dataKey="value" innerRadius={55} outerRadius={85}>
                  {operationData.map((item) => (
                    <Cell
                      key={item.key}
                      fill={OPERATION_COLORS[item.key] ?? "var(--gray-300)"}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatUsd(typeof value === "number" ? value : null)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="two-col-grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Custo por etapa do pipeline</h3>
          {stageData.length === 0 ? (
            <p className="page-subtitle">Sem consumo registrado no período.</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(220, stageData.length * 32)}>
              <BarChart data={stageData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                <XAxis type="number" fontSize={12} />
                <YAxis type="category" dataKey="etapa" width={160} fontSize={11} />
                <Tooltip formatter={(value) => formatUsd(typeof value === "number" ? value : null)} />
                <Bar dataKey="custo" fill="var(--violet-2)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 14 }}>Custo por modelo</h3>
          {summary.by_model.length === 0 ? (
            <p className="page-subtitle">Sem consumo registrado no período.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {summary.by_model.map((item) => (
                <div key={item.key}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: 13,
                      marginBottom: 4,
                    }}
                  >
                    <span>{item.label}</span>
                    <span style={{ color: "var(--content-secondary)" }}>
                      {formatUsd(item.total_usd)} · {item.pct}
                    </span>
                  </div>
                  <div
                    style={{
                      height: 8,
                      borderRadius: 4,
                      background: "var(--gray-100)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: maxModelCost > 0 ? `${(item.total_usd / maxModelCost) * 100}%` : "0%",
                        background: "var(--blue-2)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="data-table" style={{ marginBottom: 16 }}>
        <div
          className="data-table-row data-table-head"
          style={{ gridTemplateColumns: "minmax(0, 1.4fr) 120px 150px 90px 90px 120px" }}
        >
          <span>Usuário</span>
          <span>Perfil</span>
          <span>Gestor</span>
          <span>Análises</span>
          <span>Chamadas</span>
          <span style={{ textAlign: "right" }}>Custo</span>
        </div>
        {summary.top_users.length === 0 ? (
          <div className="data-table-row">
            <span className="page-subtitle">Nenhum consumo atribuído no período.</span>
          </div>
        ) : (
          summary.top_users.map((row) => (
            <div
              key={row.user_id ?? row.name}
              className="data-table-row"
              style={{ gridTemplateColumns: "minmax(0, 1.4fr) 120px 150px 90px 90px 120px" }}
            >
              <span>{row.name}</span>
              <span style={{ color: "var(--content-secondary)", fontSize: 13 }}>
                {row.role ?? "—"}
              </span>
              <span style={{ color: "var(--content-secondary)", fontSize: 13 }}>
                {row.manager_name ?? "—"}
              </span>
              <span>{row.analyses}</span>
              <span>{row.events}</span>
              <span style={{ textAlign: "right", fontWeight: 600 }}>{formatUsd(row.total_usd)}</span>
            </div>
          ))
        )}
      </div>

      <div className="data-table">
        <div
          className="data-table-row data-table-head"
          style={{ gridTemplateColumns: "minmax(0, 1.3fr) minmax(0, 1fr) 120px 90px 100px 120px" }}
        >
          <span>Participante avaliado</span>
          <span>Colaborador</span>
          <span>Criada em</span>
          <span>Entrada</span>
          <span>Tentativas</span>
          <span style={{ textAlign: "right" }}>Custo</span>
        </div>
        {summary.top_analyses.length === 0 ? (
          <div className="data-table-row">
            <span className="page-subtitle">Nenhuma análise com custo registrado no período.</span>
          </div>
        ) : (
          summary.top_analyses.map((row) => (
            <div
              key={row.analysis_id ?? `${row.participant_name}`}
              className="data-table-row"
              style={{ gridTemplateColumns: "minmax(0, 1.3fr) minmax(0, 1fr) 120px 90px 100px 120px" }}
            >
              <span>{row.participant_name ?? "Análise excluída"}</span>
              <span style={{ color: "var(--content-secondary)", fontSize: 13 }}>
                {row.owner_name ?? "—"}
              </span>
              <span style={{ fontSize: 13 }}>{formatDateTime(row.created_at)}</span>
              <span style={{ fontSize: 13 }}>{row.input_type ?? "—"}</span>
              <span>{row.attempts > 0 ? `${row.attempts + 1}ª` : "1ª"}</span>
              <span style={{ textAlign: "right", fontWeight: 600 }}>{formatUsd(row.total_usd)}</span>
            </div>
          ))
        )}
      </div>
    </>
  );
}
