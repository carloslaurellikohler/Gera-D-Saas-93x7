import type { AnalysisStatus } from "../../types/analysis";

const STEPS: { status: AnalysisStatus; label: string }[] = [
  { status: "UPLOADED", label: "Arquivo recebido" },
  { status: "TRANSCRIBING", label: "Transcrevendo" },
  { status: "TRANSCRIBED", label: "Transcrição concluída" },
  { status: "ANALYZING", label: "Analisando conversa" },
  { status: "GENERATING_REPORTS", label: "Gerando relatórios" },
  { status: "COMPLETED", label: "Concluído" },
];

interface Props {
  currentStatus: AnalysisStatus;
}

export default function StatusChecklist({ currentStatus }: Props) {
  const currentIndex = STEPS.findIndex((s) => s.status === currentStatus);

  return (
    <ul className="checklist">
      {STEPS.map((step, index) => {
        const isDone = currentIndex > index || currentStatus === "COMPLETED";
        const isActive = index === currentIndex && currentStatus !== "COMPLETED";
        return (
          <li key={step.status} className={isDone ? "done" : isActive ? "active" : ""}>
            <span className="icon">{isDone ? "✓" : isActive ? "●" : "○"}</span>
            {step.label}
          </li>
        );
      })}
    </ul>
  );
}
