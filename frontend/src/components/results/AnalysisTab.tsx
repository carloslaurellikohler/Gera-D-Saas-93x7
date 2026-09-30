import type { AnalysisResultData } from "../../types/analysis";

interface Props {
  result: AnalysisResultData | null;
  loading: boolean;
}

function ItemList({ title, items }: { title: string; items: { title: string; description: string }[] }) {
  if (items.length === 0) return null;
  return (
    <div style={{ marginBottom: 20 }}>
      <h3>{title}</h3>
      <ul>
        {items.map((item, i) => (
          <li key={i}>
            <strong>{item.title}</strong> — {item.description}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AnalysisTab({ result, loading }: Props) {
  if (loading) return <p>Carregando análise...</p>;
  if (!result) return <p>Análise indisponível.</p>;

  return (
    <div>
      <h3>Critérios avaliados</h3>
      {result.scores_by_criterion.map((c) => (
        <div key={c.key} className="criterion-score">
          <span>{c.label}</span>
          <strong>{c.score.toFixed(1)}</strong>
        </div>
      ))}

      <p style={{ marginTop: 16 }}>{result.general_reading}</p>

      <ItemList title="Pontos fortes" items={result.strengths} />
      <ItemList title="Riscos" items={result.risks} />
      <ItemList title="Oportunidades perdidas" items={result.missed_opportunities} />

      {result.suggested_questions.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3>Perguntas sugeridas</h3>
          <ul>
            {result.suggested_questions.map((q, i) => (
              <li key={i}>
                {q.question}
                <br />
                <small>{q.rationale}</small>
              </li>
            ))}
          </ul>
        </div>
      )}

      <h3>Recomendação</h3>
      <p>{result.executive_recommendation}</p>

      <h3>Avaliação final</h3>
      <p>{result.final_evaluation}</p>
    </div>
  );
}
