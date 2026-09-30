import Icon from "../components/ui/Icon";

const VERSIONS = [
  { v: "v2.3", state: "Ativa", date: "12/07/2026", n: 342 },
  { v: "v2.2", state: "Encerrada", date: "03/03/2026", n: 210 },
  { v: "v2.1", state: "Encerrada", date: "18/11/2025", n: 178 },
];

const WEIGHTS = [
  { name: "Abertura e rapport", w: 15 },
  { name: "Sondagem", w: 20 },
  { name: "Argumentação", w: 20 },
  { name: "Tratamento de objeções", w: 15 },
  { name: "Encaminhamento", w: 15 },
  { name: "Eficiência da condução", w: 15 },
];

export default function CalibrationPage() {
  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Metodologia e calibração</h1>
          <span className="page-subtitle">Versões dos critérios e da régua de faixas.</span>
        </div>
        <button className="btn btn-secondary">
          <Icon name="content_copy" size={20} />
          Nova versão a partir da v2.3
        </button>
      </div>

      <div className="info-banner" style={{ margin: "20px 0", background: "var(--background-info-n2)" }}>
        <Icon name="lock" size={22} />
        Análises concluídas mantêm a versão com que foram calculadas. Publicar uma nova versão só
        vale para análises futuras.
      </div>

      <div className="two-col-grid">
        <div className="data-table">
          <div
            className="data-table-row data-table-head"
            style={{ gridTemplateColumns: "70px 130px 1fr 90px" }}
          >
            <span>Versão</span>
            <span>Estado</span>
            <span>Publicada em</span>
            <span>Análises</span>
          </div>
          {VERSIONS.map((v) => (
            <div
              key={v.v}
              className="data-table-row"
              style={{ gridTemplateColumns: "70px 130px 1fr 90px" }}
            >
              <b>{v.v}</b>
              <span
                className="pill"
                style={{ height: "auto", padding: "3px 10px", justifySelf: "start" }}
              >
                {v.state}
              </span>
              <span className="page-subtitle">{v.date}</span>
              <b>{v.n}</b>
            </div>
          ))}
        </div>

        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Versão 2.4 · rascunho</h3>
            <span style={{ fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 6, border: "1px dashed var(--gray-900)" }}>
              Rascunho
            </span>
          </div>

          <span className="kpi-label">Régua de faixas (0–100)</span>
          <div style={{ display: "flex", height: 34, borderRadius: 8, overflow: "hidden", fontSize: 11, fontWeight: 700, color: "#fff" }}>
            <span style={{ width: "50%", background: "#B00020", display: "flex", alignItems: "center", paddingLeft: 10 }}>
              Crítico 0–49
            </span>
            <span style={{ width: "20%", background: "#C95800", display: "flex", alignItems: "center", paddingLeft: 10 }}>
              Prior. 50–69
            </span>
            <span style={{ width: "15%", background: "#A87800", display: "flex", alignItems: "center", paddingLeft: 8 }}>
              70–84
            </span>
            <span style={{ width: "15%", background: "#0F7A45", display: "flex", alignItems: "center", paddingLeft: 8 }}>
              85+
            </span>
          </div>

          <span className="kpi-label">Pesos dos critérios</span>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {WEIGHTS.map((w) => (
              <div key={w.name} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}>
                <span style={{ flex: 1 }}>{w.name}</span>
                <span
                  style={{
                    width: 64,
                    height: 36,
                    border: "1px solid var(--border-primary)",
                    borderRadius: 10,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 600,
                  }}
                >
                  {w.w}%
                </span>
              </div>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              paddingTop: 8,
              borderTop: "1px solid var(--border-secondary)",
            }}
          >
            <span style={{ fontSize: 13, fontWeight: 600, color: "#0B6B3A", display: "flex", gap: 6, alignItems: "center" }}>
              <Icon name="check_circle" size={18} filled />
              Soma = 100%
            </span>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn btn-secondary" style={{ height: 40 }}>
                Salvar rascunho
              </button>
              <button className="btn btn-primary" style={{ height: 40 }}>
                Publicar v2.4
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
