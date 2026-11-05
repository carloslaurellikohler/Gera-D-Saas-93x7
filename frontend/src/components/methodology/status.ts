import type { MethodologyStatus } from "../../types/methodology";

/** Rótulos do ciclo de vida DRAFT → PUBLISHED → ARCHIVED, compartilhados pela tabela e pelo editor. */
export const STATUS_LABEL: Record<MethodologyStatus, string> = {
  DRAFT: "Rascunho",
  PUBLISHED: "Ativa",
  ARCHIVED: "Encerrada",
};
