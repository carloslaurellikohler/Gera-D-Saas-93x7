import FarolBadge, { type FarolLevel } from "../components/ui/FarolBadge";
import Icon from "../components/ui/Icon";

const KPIS = [
  { label: "Análises no mês", value: "128", description: "+18% vs. mês anterior" },
  { label: "Nota média geral", value: "71", description: "Faixa: Atenção" },
  { label: "Profissionais ativos", value: "34", description: "de 41 cadastrados" },
  { label: "Tempo médio de análise", value: "3min", description: "do envio ao resultado" },
];

const DISTRIBUTION: { level: FarolLevel; count: number; pct: string }[] = [
  { level: "excelente", count: 28, pct: "22%" },
  { level: "atencao", count: 52, pct: "41%" },
  { level: "prioritario", count: 34, pct: "27%" },
  { level: "critico", count: 14, pct: "10%" },
];

const BOARD = [
  { name: "Camila Ferraz", n: 12, avg: 69, level: "prioritario" as FarolLevel, trend: "down" },
  { name: "Bruno Tavares", n: 9, avg: 74, level: "atencao" as FarolLevel, trend: "up" },
  { name: "Marina Duarte", n: 15, avg: 88, level: "excelente" as FarolLevel, trend: "up" },
  { name: "Rafael Nogueira", n: 7, avg: 45, level: "critico" as FarolLevel, trend: "down" },
  { name: "Paula Rezende", n: 11, avg: 79, level: "atencao" as FarolLevel, trend: "flat" },
];

const TREND_ICON = { up: "trending_up", down: "trending_down", flat: "trending_flat" };
const TREND_COLOR = { up: "#0B6B3A", down: "#A10019", flat: "var(--content-secondary)" };

export default function AdminDashboardPage() {
  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Painel administrativo</h1>
          <span className="page-subtitle">Visão agregada de todas as equipes.</span>
        </div>
        <span className="search-field">
          Últimos 30 dias
          <Icon name="expand_more" size={20} />
        </span>
      </div>

      <div className="kpi-grid" style={{ margin: "24px 0" }}>
        {KPIS.map((k) => (
          <div key={k.label} className="kpi-card">
            <span className="kpi-label">{k.label}</span>
            <span className="kpi-value">{k.value}</span>
            <span className="kpi-description">{k.description}</span>
          </div>
        ))}
      </div>

      <div className="two-col-grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Nota média por semana</h3>
          <p className="page-subtitle">Gráfico de evolução disponível quando houver dados suficientes.</p>
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 14 }}>Distribuição por farol</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {DISTRIBUTION.map((d) => (
              <div key={d.level} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
                <span style={{ flex: 1 }}>
                  <FarolBadge level={d.level} />
                </span>
                <b>{d.count}</b>
                <span style={{ width: 40, textAlign: "right", color: "var(--content-secondary)" }}>{d.pct}</span>
              </div>
            ))}
          </div>
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
        {BOARD.map((b) => (
          <div
            key={b.name}
            className="data-table-row"
            style={{ gridTemplateColumns: "minmax(0,1.4fr) 100px 100px 220px 110px" }}
          >
            <b>{b.name}</b>
            <span>{b.n}</span>
            <b>{b.avg}</b>
            <FarolBadge level={b.level} />
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 600, color: TREND_COLOR[b.trend as keyof typeof TREND_COLOR] }}>
              <Icon name={TREND_ICON[b.trend as keyof typeof TREND_ICON]} size={18} />
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
