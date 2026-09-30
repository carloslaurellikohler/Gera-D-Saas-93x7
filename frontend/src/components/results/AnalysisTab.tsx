import { useState } from "react";
import type { AnalysisResultData } from "../../types/analysis";
import FarolBadge, { farolLevelForScore } from "../ui/FarolBadge";
import Icon from "../ui/Icon";

interface Props {
  result: AnalysisResultData | null;
  loading: boolean;
}

function ItemList({ title, items }: { title: string; items: { title: string; description: string }[] }) {
  if (items.length === 0) return null;
  return (
    <div className="card">
      <h3 style={{ marginBottom: 10 }}>{title}</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13, lineHeight: 1.6 }}>
        {items.map((item, i) => (
          <span key={i}>
            <strong>{item.title}</strong> — {item.description}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function AnalysisTab({ result, loading }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  if (loading) return <p className="page-subtitle">Carregando análise...</p>;
  if (!result) return <p className="page-subtitle">Análise indisponível.</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {result.scores_by_criterion.map((c, i) => {
          const level = farolLevelForScore(c.score);
          const open = openKey === c.key;
          return (
            <div key={c.key} className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div
                style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 20px", cursor: "pointer" }}
                onClick={() => setOpenKey(open ? null : c.key)}
              >
                <span
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "100px",
                    background: "var(--gerad-navy-100)",
                    color: "var(--gerad-navy)",
                    fontWeight: 700,
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ flex: 1, fontWeight: 600, fontSize: 15 }}>{c.label}</span>
                <b style={{ fontFamily: "var(--font-brand)", fontSize: 22 }}>{Math.round(c.score)}</b>
                <FarolBadge level={level} />
                <Icon name={open ? "expand_less" : "expand_more"} size={22} color="var(--content-secondary)" />
              </div>
              {open && (
                <div style={{ borderTop: "1px solid var(--border-secondary)", padding: 20, background: "var(--gray-50)" }}>
                  <span className="kpi-label">Leitura</span>
                  <p style={{ fontSize: 13, lineHeight: 1.6, marginTop: 6 }}>{c.reading}</p>
                  <span className="kpi-label">Análise</span>
                  <p style={{ fontSize: 13, lineHeight: 1.6, marginTop: 6 }}>{c.analysis}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p style={{ fontSize: 14, lineHeight: 1.65 }}>{result.general_reading}</p>

      <ItemList title="Pontos fortes" items={result.strengths} />
      <ItemList title="Riscos" items={result.risks} />
      <ItemList title="Oportunidades perdidas" items={result.missed_opportunities} />

      {result.suggested_questions.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: 10 }}>Perguntas sugeridas</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {result.suggested_questions.map((q, i) => (
              <div key={i} style={{ display: "flex", gap: 10, fontSize: 13, lineHeight: 1.5, alignItems: "flex-start" }}>
                <Icon name="help" size={18} color="var(--gerad-gold-700)" />
                <span>
                  {q.question}
                  <br />
                  <small style={{ color: "var(--content-secondary)" }}>{q.rationale}</small>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Avaliação final</h3>
        <p style={{ fontSize: 14, lineHeight: 1.65 }}>{result.final_evaluation}</p>
      </div>
    </div>
  );
}
