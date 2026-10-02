// Espelha app/core/constants.py CriterionKey no backend.
export type CriterionKey =
  | "posicionamento"
  | "conexao"
  | "sondagem"
  | "direcionamento"
  | "encaminhamento"
  | "eficiencia_conducao";

export type ContentKind = "FILE" | "LINK";

export interface ContentResponse {
  id: string;
  title: string;
  description: string | null;
  criterion_key: CriterionKey | null;
  kind: ContentKind;
  file_path: string | null;
  external_url: string | null;
  uploaded_by_id: string | null;
  created_at: string;
}

export interface CreateContentPayload {
  title: string;
  description?: string;
  criterion_key?: CriterionKey;
  kind: ContentKind;
  file?: File;
  external_url?: string;
}
