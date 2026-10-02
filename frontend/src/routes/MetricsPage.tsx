import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import EmptyState from "../components/ui/EmptyState";
import Icon from "../components/ui/Icon";
import { useMetricsEvolution } from "../hooks/useMetricsEvolution";
import { formatDate } from "../lib/format";
import type { MetricsPeriod } from "../types/metrics";

const PERIOD_LABELS: Record<MetricsPeriod, string> = {
  "30d": "Últimos 30 dias",
  "90d": "Últimos 90 dias",
  "6m": "Últimos 6 meses",
};

export default function MetricsPage() {
  const [period, setPeriod] = useState<MetricsPeriod>("90d");
  const { data, isLoading, isError } = useMetricsEvolution(period);

  const hasCurrentPeriodData = (data?.trend.length ?? 0) > 0;

  const trendData = useMemo(
    () =>
      (data?.trend ?? []).map((t) => ({
        period: formatDate(t.period_start),
        geral: t.avg_overall_score,
        pilar93: t.avg_pilar_93,
        pilar7: t.avg_pilar_7,
      })),
    [data],
  );

  const radarData = useMemo(() => (data?.radar ?? []).map((r) => ({ ...r })), [data]);
  const hasPreviousPeriodData = radarData.some((r) => r.previous_score !== null);

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Métricas e evolução</h1>
          <span className="page-subtitle">
            Acompanhe a evolução ao longo do tempo e compare critérios.
          </span>
        </div>
        <span className="search-field">
          <select
            aria-label="Período"
            value={period}
            onChange={(e) => setPeriod(e.target.value as MetricsPeriod)}
            style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
          >
            {(Object.keys(PERIOD_LABELS) as MetricsPeriod[]).map((key) => (
              <option key={key} value={key}>
                {PERIOD_LABELS[key]}
              </option>
            ))}
          </select>
          <Icon name="expand_more" size={20} />
        </span>
      </div>

      {isLoading && <p className="page-subtitle">Carregando...</p>}
      {isError && <p className="error-text">Não foi possível carregar os indicadores.</p>}

      {data && (
        <div className="two-col-grid" style={{ marginTop: 20 }}>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Evolução temporal</h3>
            {!hasCurrentPeriodData ? (
              <EmptyState
                icon="show_chart"
                title="Sem análises concluídas no período"
                description="O gráfico de evolução aparece quando houver análises concluídas na janela selecionada."
              />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                  <XAxis dataKey="period" fontSize={12} />
                  <YAxis domain={[0, 10]} fontSize={12} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="geral"
                    name="Nota geral"
                    stroke="var(--gerad-navy)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="pilar93"
                    name="Pilar 93"
                    stroke="var(--blue)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="pilar7"
                    name="Pilar 7"
                    stroke="var(--orange)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Comparação por critério</h3>
            {!hasCurrentPeriodData ? (
              <EmptyState
                icon="radar"
                title="Sem análises concluídas no período"
                description="O radar dos 6 critérios aparece quando houver análises concluídas na janela selecionada."
              />
            ) : (
              <>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="var(--border-secondary)" />
                    <PolarAngleAxis dataKey="label" fontSize={12} />
                    <PolarRadiusAxis domain={[0, 10]} fontSize={11} />
                    <Tooltip />
                    <Radar
                      name="Período atual"
                      dataKey="score"
                      stroke="var(--gerad-navy)"
                      fill="var(--gerad-navy)"
                      fillOpacity={0.25}
                    />
                    {hasPreviousPeriodData && (
                      <Radar
                        name="Período anterior"
                        dataKey="previous_score"
                        stroke="var(--gerad-gold)"
                        fill="var(--gerad-gold)"
                        fillOpacity={0.12}
                        strokeDasharray="4 3"
                      />
                    )}
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
                {!hasPreviousPeriodData && (
                  <p className="page-subtitle" style={{ marginTop: 8 }}>
                    Comparação com período anterior indisponível.
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
