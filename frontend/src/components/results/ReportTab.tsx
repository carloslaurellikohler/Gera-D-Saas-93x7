import { reportUrl } from "../../api/client";
import Icon from "../ui/Icon";

interface Props {
  analysisId: string;
}

const REPORTS = [
  { kind: "executivo" as const, name: "Executivo", desc: "Visão geral para o gestor, com nota geral e recomendação." },
  { kind: "detalhado" as const, name: "Detalhado", desc: "Critério a critério, com evidências e perguntas sugeridas." },
];

export default function ReportTab({ analysisId }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {REPORTS.map((r) => (
          <div key={r.kind} className="card" style={{ display: "flex", gap: 24 }}>
            <div
              style={{
                width: 90,
                height: 120,
                flex: "none",
                border: "1px solid var(--border-primary)",
                borderRadius: 6,
                background: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--content-tertiary)",
              }}
            >
              <Icon name="description" size={32} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
              <span style={{ fontFamily: "var(--font-brand)", fontWeight: 600, fontSize: 20, color: "var(--gerad-navy)" }}>
                Relatório {r.name}
              </span>
              <span className="page-subtitle" style={{ fontSize: 13 }}>
                {r.desc}
              </span>
              <div style={{ display: "flex", gap: 10, marginTop: "auto" }}>
                <a
                  className="btn btn-primary"
                  style={{ height: 40, padding: "0 16px" }}
                  href={reportUrl(analysisId, r.kind)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Icon name="download" size={18} />
                  Baixar PDF
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="info-banner">
        <Icon name="history" size={22} color="var(--gerad-navy)" />
        Relatórios gerados a partir da metodologia 93x7® vigente. Resultados antigos não são
        recalculados quando a metodologia muda.
      </div>
    </div>
  );
}
