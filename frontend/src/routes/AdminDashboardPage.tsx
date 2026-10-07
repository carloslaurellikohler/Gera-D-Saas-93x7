import { useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import BoardTable from "../components/ui/BoardTable";
import FarolBadge, { toFarolLevel } from "../components/ui/FarolBadge";
import Icon from "../components/ui/Icon";
import { useDashboardStats } from "../hooks/useDashboardStats";
import { formatDate } from "../lib/format";
import type { DashboardPeriod } from "../types/dashboard";

const PERIOD_LABELS: Record<DashboardPeriod, string> = {
  "30d": "Últimos 30 dias",
  "90d": "Últimos 90 dias",
  "6m": "Últimos 6 meses",
};

export default function AdminDashboardPage() {
  const [period, setPeriod] = useState<DashboardPeriod>("6m");
  const { data, isLoading, isError } = useDashboardStats(period);

  const totalVolume = useMemo(
    () => data?.volume_by_status.reduce((sum, v) => sum + v.count, 0) ?? 0,
    [data],
  );

  const avgScore = useMemo(() => {
    if (!data) return null;
    const scored = data.trend.filter((t) => t.avg_score !== null);
    const totalCount = scored.reduce((sum, t) => sum + t.count, 0);
    if (totalCount === 0) return null;
    const weighted = scored.reduce((sum, t) => sum + (t.avg_score ?? 0) * t.count, 0);
    return weighted / totalCount;
  }, [data]);

  const predominantFarol = useMemo(() => {
    if (!data || data.farol_distribution.length === 0) return null;
    return data.farol_distribution.reduce((max, item) => (item.count > max.count ? item : max));
  }, [data]);

  const chartData = useMemo(
    () =>
      (data?.trend ?? []).map((t) => ({
        period: formatDate(t.period_start),
        nota: t.avg_score,
      })),
    [data],
  );

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Painel administrativo</h1>
          <span className="page-subtitle">Visão agregada de todas as equipes.</span>
        </div>
        <span className="search-field">
          <select
            aria-label="Período"
            value={period}
            onChange={(e) => setPeriod(e.target.value as DashboardPeriod)}
            style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
          >
            {(Object.keys(PERIOD_LABELS) as DashboardPeriod[]).map((key) => (
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
        <>
          <div className="kpi-grid" style={{ margin: "24px 0" }}>
            <div className="kpi-card">
              <span className="kpi-label">Análises no período</span>
              <span className="kpi-value">{totalVolume}</span>
              <span className="kpi-description">{PERIOD_LABELS[period]}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Nota média geral</span>
              <span className="kpi-value">{avgScore !== null ? avgScore.toFixed(1) : "—"}</span>
              <span className="kpi-description">Escala de 0 a 10</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Profissionais avaliados</span>
              <span className="kpi-value">{data.board?.length ?? "—"}</span>
              <span className="kpi-description">com análises concluídas</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Farol predominante</span>
              <span className="kpi-value" style={{ fontSize: 18 }}>
                {predominantFarol ? <FarolBadge level={toFarolLevel(predominantFarol.level)} /> : "—"}
              </span>
              <span className="kpi-description">{predominantFarol?.pct ?? ""}</span>
            </div>
          </div>

          <div className="two-col-grid" style={{ marginBottom: 16 }}>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Nota média por semana</h3>
              {chartData.length === 0 ? (
                <p className="page-subtitle">Gráfico de evolução disponível quando houver dados suficientes.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-secondary)" />
                    <XAxis dataKey="period" fontSize={12} />
                    <YAxis domain={[0, 10]} fontSize={12} />
                    <Tooltip />
                    <Line type="monotone" dataKey="nota" stroke="var(--gerad-navy)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="card">
              <h3 style={{ marginBottom: 14 }}>Distribuição por farol</h3>
              {data.farol_distribution.length === 0 ? (
                <p className="page-subtitle">Sem análises concluídas no período.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {data.farol_distribution.map((d) => (
                    <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
                      <span style={{ flex: 1 }}>
                        <FarolBadge level={toFarolLevel(d.level)} />
                      </span>
                      <b>{d.count}</b>
                      <span style={{ width: 40, textAlign: "right", color: "var(--content-secondary)" }}>
                        {d.pct}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <BoardTable
            title="Quadro individual"
            nameColumnLabel="Participante"
            rows={(data.board ?? []).map((b) => ({ id: b.pb_id, ...b }))}
            emptyMessage="Nenhuma análise concluída no período."
          />
        </>
      )}
    </div>
  );
}
