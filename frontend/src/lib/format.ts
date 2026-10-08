export function formatDurationSeconds(seconds: number | null): string {
  if (seconds === null) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}min`;
  return `${minutes} min`;
}

/**
 * Custo em dólares. Usa 4 casas abaixo de 1 centavo porque o custo de uma única chamada
 * costuma viver nessa faixa (um embedding de pergunta custa fração de centavo) — com 2
 * casas a tabela de eventos mostraria "US$ 0,00" em quase toda linha.
 */
export function formatUsd(value: number | null): string {
  if (value === null) return "—";
  if (value !== 0 && Math.abs(value) < 0.01) {
    return `US$ ${value.toLocaleString("pt-BR", {
      minimumFractionDigits: 4,
      maximumFractionDigits: 6,
    })}`;
  }
  return `US$ ${value.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Equivalente aproximado em reais, só para exibição ao lado do valor em dólar. A taxa é
 * manual (cadastrada pelo ADMIN) e nenhum valor em BRL é persistido no banco.
 */
export function formatBrlFromUsd(usd: number | null, rate: number | null): string | null {
  if (usd === null || rate === null) return null;
  return `≈ R$ ${(usd * rate).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
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
