export function formatDurationSeconds(seconds: number | null): string {
  if (seconds === null) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}min`;
  return `${minutes} min`;
}

export function formatDate(isoString: string | null): string {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatDateTime(isoString: string | null): string {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleString("pt-BR");
}

const STATUS_LABELS: Record<string, string> = {
  CREATED: "Criado",
  UPLOADED: "Enviado",
  TRANSCRIBING: "Transcrevendo",
  TRANSCRIBED: "Transcrito",
  ANALYZING: "Analisando",
  GENERATING_REPORTS: "Gerando relatórios",
  COMPLETED: "Concluído",
  FAILED: "Falhou",
};

export function formatStatus(status: string): string {
  return STATUS_LABELS[status] ?? status;
}
