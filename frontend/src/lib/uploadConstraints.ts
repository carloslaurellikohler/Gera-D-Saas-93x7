export type InputTypeChoice = "texto" | "audio" | "video";

// Espelha app/core/constants.py ALLOWED_EXTENSIONS no backend — a engine só reconhece
// .docx/.txt/.mp3/.mp4 hoje (ver README, seção "Formatos de entrada suportados").
export const EXTENSIONS_BY_CHOICE: Record<InputTypeChoice, string[]> = {
  texto: [".docx", ".txt"],
  audio: [".mp3"],
  video: [".mp4"],
};

export const MAX_UPLOAD_MB = 100;

export function isExtensionAllowed(fileName: string, choice: InputTypeChoice): boolean {
  const lower = fileName.toLowerCase();
  return EXTENSIONS_BY_CHOICE[choice].some((ext) => lower.endsWith(ext));
}
