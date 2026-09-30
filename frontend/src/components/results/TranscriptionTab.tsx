import type { Transcript } from "../../types/analysis";

interface Props {
  transcription: Transcript | null;
  loading: boolean;
}

export default function TranscriptionTab({ transcription, loading }: Props) {
  if (loading) return <p>Carregando transcrição...</p>;
  if (!transcription) return <p>Transcrição indisponível.</p>;

  if (transcription.turns.length === 0) {
    return <p>Nenhum conteúdo transcrito.</p>;
  }

  return (
    <div>
      {transcription.turns.map((turn, i) => (
        <p key={i}>
          <strong>{turn.speaker ?? "—"}:</strong> {turn.text}
        </p>
      ))}
    </div>
  );
}
