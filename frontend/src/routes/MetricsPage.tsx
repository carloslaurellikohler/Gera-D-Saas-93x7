import Icon from "../components/ui/Icon";

const COMPARE = [
  { name: "Abertura e rapport", a: 62, b: 78 },
  { name: "Sondagem", a: 48, b: 58 },
  { name: "Argumentação", a: 70, b: 81 },
  { name: "Objeções", a: 55, b: 66 },
  { name: "Encaminhamento", a: 60, b: 66 },
  { name: "Eficiência da condução", a: 40, b: 47 },
];

export default function MetricsPage() {
  return (
    <div>
      <div className="page-title-group">
        <h1>Métricas e evolução</h1>
        <span className="page-subtitle">
          Acompanhe a evolução ao longo do tempo e compare critérios.
        </span>
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "20px 0" }}>
        <span className="search-field">
          <Icon name="calendar_month" size={18} />
          Últimos 90 dias
        </span>
        <span className="search-field">
          <Icon name="person" size={18} />
          Todos os participantes
        </span>
        <span className="search-field">
          <Icon name="flag" size={18} />
          Todos os objetivos
        </span>
      </div>

      <div className="two-col-grid">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Nota geral da equipe</h3>
            <span style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13, fontWeight: 600, color: "#0B6B3A" }}>
              <Icon name="trending_up" size={18} />
              +21 pontos em 90 dias
            </span>
          </div>
          <p className="page-subtitle" style={{ marginTop: 12 }}>
            Gráfico de evolução disponível quando houver análises suficientes no período.
          </p>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 14 }}>Comparação por critério</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {COMPARE.map((c) => (
              <div key={c.name} style={{ display: "flex", flexDirection: "column", gap: 5, fontSize: 12 }}>
                <span style={{ display: "flex", justifyContent: "space-between", fontWeight: 600 }}>
                  <span>{c.name}</span>
                  <span>
                    {c.a} → {c.b}
                  </span>
                </span>
                <span style={{ height: 6, borderRadius: 3, background: "var(--gray-100)", overflow: "hidden" }}>
                  <span style={{ display: "block", height: "100%", width: `${c.a}%`, background: "var(--gray-300)" }} />
                </span>
                <span style={{ height: 6, borderRadius: 3, background: "var(--gray-100)", overflow: "hidden" }}>
                  <span style={{ display: "block", height: "100%", width: `${c.b}%`, background: "var(--gerad-navy)" }} />
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
