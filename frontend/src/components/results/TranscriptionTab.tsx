import type { Transcript } from "../../types/analysis";

interface Props {
  transcription: Transcript | null;
  loading: boolean;
}

export default function TranscriptionTab({ transcription, loading }: Props) {
  if (loading) return <p className="page-subtitle">Carregando transcrição...</p>;
  if (!transcription) return <p className="page-subtitle">Transcrição indisponível.</p>;

  if (transcription.turns.length === 0) {
    return <p className="page-subtitle">Nenhum conteúdo transcrito.</p>;
  }

  return (
    <div className="card" style={{ padding: "12px 28px" }}>
      {transcription.turns.map((turn, i) => (
        <div
          key={i}
          style={{
            display: "grid",
            gridTemplateColumns: "60px 1fr",
            gap: 16,
            padding: "16px 0",
            borderBottom:
              i < transcription.turns.length - 1 ? "1px solid var(--border-tertiary)" : "none",
          }}
        >
          <span
            style={{
              height: 24,
              borderRadius: 6,
              background: "var(--gray-100)",
              color: "var(--gerad-navy)",
              fontSize: 11,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {turn.speaker ?? "—"}
          </span>
          <span style={{ fontSize: 14, lineHeight: 1.6 }}>{turn.text}</span>
        </div>
      ))}
    </div>
  );
}
