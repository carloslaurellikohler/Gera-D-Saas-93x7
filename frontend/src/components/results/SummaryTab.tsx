import type { AnalysisResponse, AnalysisResultData } from "../../types/analysis";
import { formatDurationSeconds } from "../../lib/format";
import ScoreCard from "../ui/ScoreCard";
import { toFarolLevel } from "../ui/FarolBadge";
import Icon from "../ui/Icon";

interface Props {
  analysis: AnalysisResponse;
  result: AnalysisResultData | null;
  resultLoading: boolean;
}

export default function SummaryTab({ analysis, result, resultLoading }: Props) {
  if (resultLoading) {
    return <p className="page-subtitle">Carregando resumo...</p>;
  }

  if (!result) {
    return <p className="page-subtitle">Resumo indisponível.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <p className="page-subtitle">
        {analysis.objective}
        {analysis.objective_complement ? `: ${analysis.objective_complement}` : ""}
        {" · "}
        {formatDurationSeconds(analysis.duration_seconds)}
        {" · "}
        {result.pb_name} com {result.cs_name}
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20 }}>
        <ScoreCard
          label="Nota geral"
          sub={result.overall_band_label}
          score={Math.round(result.overall_score)}
          level={toFarolLevel(result.overall_farol_level)}
          size="lg"
        />
        {result.scores_by_criterion.slice(0, 3).map((c) => (
          <ScoreCard key={c.key} label={c.label} score={Math.round(c.score)} />
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", gap: 20 }}>
        <div className="card">
          <h3 style={{ marginBottom: 14 }}>Os critérios</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {result.scores_by_criterion.map((c) => (
              <div key={c.key} style={{ display: "grid", gridTemplateColumns: "150px 1fr 30px", gap: 12, alignItems: "center", fontSize: 13 }}>
                <span style={{ fontWeight: 500 }}>{c.label}</span>
                <span style={{ height: 8, borderRadius: 4, background: "var(--gray-100)", overflow: "hidden" }}>
                  <span style={{ display: "block", height: "100%", width: `${(c.score / 10) * 100}%`, background: "var(--gerad-navy)" }} />
                </span>
                <b style={{ textAlign: "right" }}>{Math.round(c.score)}</b>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 14 }}>Diagnóstico executivo</h3>
          <p style={{ fontSize: 14, lineHeight: 1.65 }}>{result.executive_diagnosis}</p>
          <div className="info-banner" style={{ background: "var(--background-brand-primary-n5)", marginTop: 12 }}>
            <Icon name="school" size={20} color="var(--gerad-navy)" />
            <span>
              <b>Recomendação:</b> {result.executive_recommendation}
            </span>
          </div>
        </div>
      </div>

      <p style={{ fontSize: 14, lineHeight: 1.65 }}>{result.overall_classification_text}</p>
    </div>
  );
}
