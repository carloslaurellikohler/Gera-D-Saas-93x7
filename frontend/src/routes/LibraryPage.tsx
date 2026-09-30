import { useState } from "react";
import Icon from "../components/ui/Icon";

type LibraryTab = "trilhas" | "materiais" | "andamento";

const TABS: { key: LibraryTab; label: string }[] = [
  { key: "trilhas", label: "Trilhas sugeridas" },
  { key: "materiais", label: "Materiais de apoio" },
  { key: "andamento", label: "Em andamento" },
];

const TRAILS = [
  { icon: "record_voice_over", crit: "Sondagem", title: "Sondagem consultiva", meta: "4 módulos · 35 min" },
  { icon: "call_split", crit: "Encaminhamento", title: "Fechamento com próximos passos", meta: "3 módulos · 22 min" },
  { icon: "speed", crit: "Eficiência da condução", title: "Conduzindo reuniões objetivas", meta: "5 módulos · 40 min" },
];

export default function LibraryPage() {
  const [tab, setTab] = useState<LibraryTab>("trilhas");

  return (
    <div>
      <div className="page-title-group">
        <h1>Biblioteca</h1>
        <span className="page-subtitle">Materiais e trilhas sugeridos a partir dos seus resultados.</span>
      </div>

      <div className="tabs" style={{ margin: "20px 0" }}>
        {TABS.map((t) => (
          <button key={t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "trilhas" && (
        <>
          <div className="info-banner" style={{ marginBottom: 16 }}>
            <Icon name="auto_awesome" size={22} />
            <span>
              Sugestões baseadas na sua última análise: <b>Sondagem</b>, <b>Encaminhamento</b> e{" "}
              <b>Eficiência da condução</b>.
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
            {TRAILS.map((t) => (
              <div key={t.title} className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div
                  style={{
                    height: 120,
                    background: "var(--background-brand-secondary-n5)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Icon name={t.icon} size={48} color="var(--gerad-navy)" />
                </div>
                <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                  <span className="pill" style={{ alignSelf: "flex-start", height: "auto", padding: "3px 10px" }}>
                    {t.crit}
                  </span>
                  <b style={{ fontFamily: "var(--font-brand)", fontSize: 17, color: "var(--gerad-navy)" }}>
                    {t.title}
                  </b>
                  <span className="page-subtitle" style={{ fontSize: 12 }}>
                    {t.meta}
                  </span>
                  <button className="btn btn-secondary" style={{ height: 40 }}>
                    Começar trilha
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "materiais" && <p className="page-subtitle">Nenhum material de apoio disponível ainda.</p>}
      {tab === "andamento" && <p className="page-subtitle">Você ainda não iniciou nenhuma trilha.</p>}
    </div>
  );
}
