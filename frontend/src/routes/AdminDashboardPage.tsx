import { useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
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

const TREND_ICON = { up: "trending_up", down: "trending_down", flat: "trending_flat" };
const TREND_COLOR = { up: "#0B6B3A", down: "#A10019", flat: "var(--content-secondary)" };

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

          <div className="data-table">
            <div style={{ padding: "18px 24px" }}>
              <h3>Quadro individual</h3>
            </div>
            <div
              className="data-table-row data-table-head"
              style={{ gridTemplateColumns: "minmax(0,1.4fr) 100px 100px 220px 110px" }}
            >
              <span>Participante</span>
              <span>Análises</span>
              <span>Nota média</span>
              <span>Farol</span>
              <span>Tendência</span>
            </div>
            {(data.board ?? []).map((b) => (
              <div
                key={b.pb_id}
                className="data-table-row"
                style={{ gridTemplateColumns: "minmax(0,1.4fr) 100px 100px 220px 110px" }}
              >
                <b>{b.name}</b>
                <span>{b.count}</span>
                <b>{b.avg_score ?? "—"}</b>
                {b.level ? <FarolBadge level={toFarolLevel(b.level)} /> : <span>—</span>}
                {b.trend && (
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      fontWeight: 600,
                      color: TREND_COLOR[b.trend],
                    }}
                  >
                    <Icon name={TREND_ICON[b.trend]} size={18} />
                  </span>
                )}
              </div>
            ))}
            {data.board?.length === 0 && (
              <div className="data-table-row">
                <span className="page-subtitle">Nenhuma análise concluída no período.</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
