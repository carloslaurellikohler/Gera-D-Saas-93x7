import type { AnalysisStatus } from "../../types/analysis";
import Icon from "../ui/Icon";

const STEPS: { status: AnalysisStatus; label: string; description: string }[] = [
  { status: "UPLOADED", label: "Arquivo recebido", description: "O envio foi concluído com sucesso." },
  { status: "TRANSCRIBING", label: "Transcrevendo", description: "Convertendo áudio ou vídeo em texto." },
  {
    status: "TRANSCRIBED",
    label: "Transcrição concluída",
    description: "O conteúdo da interação já está em texto.",
  },
  { status: "ANALYZING", label: "Analisando conversa", description: "Aplicando os 6 critérios da metodologia 93x7®." },
  { status: "GENERATING_REPORTS", label: "Gerando relatórios", description: "Montando o relatório executivo e o detalhado." },
  { status: "COMPLETED", label: "Concluído", description: "Resultado disponível para consulta." },
];

interface Props {
  currentStatus: AnalysisStatus;
}

export default function StatusChecklist({ currentStatus }: Props) {
  const currentIndex = STEPS.findIndex((s) => s.status === currentStatus);

  return (
    <ul className="ui-stepper">
      {STEPS.map((step, index) => {
        const isDone = currentIndex > index || currentStatus === "COMPLETED";
        const isActive = index === currentIndex && currentStatus !== "COMPLETED";
        const state = isDone ? "done" : isActive ? "active" : "pending";
        return (
          <li key={step.status} className={`ui-stepper-item ui-stepper-item-${state}`}>
            <span className="ui-stepper-rail">
              <span className="ui-stepper-circle">
                <Icon
                  name={isDone ? "check" : isActive ? "progress_activity" : "radio_button_unchecked"}
                  size={18}
                  filled={isDone}
                  spin={isActive}
                />
              </span>
              {index < STEPS.length - 1 && <span className="ui-stepper-line" />}
            </span>
            <span className="ui-stepper-text">
              <span className="ui-stepper-label">{step.label}</span>
              <span className="ui-stepper-description">{step.description}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
