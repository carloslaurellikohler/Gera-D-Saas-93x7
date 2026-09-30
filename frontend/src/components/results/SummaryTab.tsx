import type { AnalysisResponse, AnalysisResultData } from "../../types/analysis";
import { formatDurationSeconds } from "../../lib/format";

interface Props {
  analysis: AnalysisResponse;
  result: AnalysisResultData | null;
  resultLoading: boolean;
}

export default function SummaryTab({ analysis, result, resultLoading }: Props) {
  return (
    <div>
      <h2>{analysis.participant_name}</h2>
      <p>
        {analysis.objective}
        {analysis.objective_complement ? `: ${analysis.objective_complement}` : ""}
        {" · "}
        {formatDurationSeconds(analysis.duration_seconds)}
      </p>

      {resultLoading && <p>Carregando resumo...</p>}

      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          <p>
            <strong>Nota geral:</strong> {result.overall_score.toFixed(1)} —{" "}
            {result.overall_band_label}
          </p>
          <p>{result.overall_classification_text}</p>
          <h3>Diagnóstico executivo</h3>
          <p>{result.executive_diagnosis}</p>
        </div>
      )}
    </div>
  );
}
