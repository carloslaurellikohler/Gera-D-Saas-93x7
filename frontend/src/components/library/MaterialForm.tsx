import { useState } from "react";
import { ApiError } from "../../api/client";
import { useCreateContent } from "../../hooks/useCreateContent";
import { useUpdateContent } from "../../hooks/useUpdateContent";
import { CONTENT_EXTENSIONS, CONTENT_MAX_UPLOAD_MB } from "../../lib/contentUploadConstraints";
import type { ContentKind, ContentResponse, CriterionKey } from "../../types/content";
import FileDropzone from "../forms/FileDropzone";
import ErrorBanner from "../ui/ErrorBanner";
import Icon from "../ui/Icon";

const CRITERION_LABELS: Record<CriterionKey, string> = {
  posicionamento: "Posicionamento",
  conexao: "Conexão",
  sondagem: "Sondagem",
  direcionamento: "Direcionamento",
  encaminhamento: "Encaminhamento",
  eficiencia_conducao: "Eficiência da condução",
};

const CRITERION_OPTIONS = Object.entries(CRITERION_LABELS) as [CriterionKey, string][];

export default function MaterialForm({ onDone, editing }: { onDone: () => void; editing?: ContentResponse }) {
  const createContent = useCreateContent();
  const updateContent = useUpdateContent();

  const [title, setTitle] = useState(editing?.title ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");
  const [criterionKey, setCriterionKey] = useState<CriterionKey | "">(editing?.criterion_key ?? "");
  const [kind, setKind] = useState<ContentKind>(editing?.kind ?? "LINK");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [externalUrl, setExternalUrl] = useState(editing?.external_url ?? "");
  const [error, setError] = useState<string | null>(null);

  const isPending = editing ? updateContent.isPending : createContent.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (!title.trim()) {
      setError("Informe um título para o material.");
      return;
    }
    if (!editing && kind === "FILE" && !file) {
      setError("Selecione um arquivo PDF.");
      return;
    }
    if (kind === "LINK" && !externalUrl.trim()) {
      setError("Informe a URL externa.");
      return;
    }
    try {
      if (editing) {
        await updateContent.mutateAsync({
          id: editing.id,
          payload: {
            title,
            description: description || undefined,
            criterion_key: criterionKey || undefined,
            file: kind === "FILE" ? file ?? undefined : undefined,
            external_url: kind === "LINK" ? externalUrl : undefined,
          },
        });
      } else {
        await createContent.mutateAsync({
          title,
          description: description || undefined,
          criterion_key: criterionKey || undefined,
          kind,
          file: kind === "FILE" ? file ?? undefined : undefined,
          external_url: kind === "LINK" ? externalUrl : undefined,
        });
      }
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Erro ao ${editing ? "salvar" : "cadastrar"} material.`);
    }
  };

  return (
    <div>
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="form-field" style={{ marginTop: error ? 18 : 0 }}>
        <label htmlFor="material-title">Título</label>
        <input id="material-title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>

      <div className="form-field">
        <label htmlFor="material-description">Descrição</label>
        <input
          id="material-description"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className="form-row">
        <div className="form-field">
          <label htmlFor="material-criterion">Critério associado</label>
          <select
            id="material-criterion"
            value={criterionKey}
            onChange={(e) => setCriterionKey(e.target.value as CriterionKey | "")}
          >
            <option value="">Nenhum</option>
            {CRITERION_OPTIONS.map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label>Tipo de material</label>
          {editing ? (
            <span className="page-subtitle">{kind === "FILE" ? "Arquivo PDF" : "Link externo"}</span>
          ) : (
            <div className="input-type-choice">
              <button type="button" className={kind === "LINK" ? "active" : ""} onClick={() => setKind("LINK")}>
                Link externo
              </button>
              <button type="button" className={kind === "FILE" ? "active" : ""} onClick={() => setKind("FILE")}>
                Arquivo PDF
              </button>
            </div>
          )}
        </div>
      </div>

      {kind === "FILE" ? (
        <div className="form-field">
          <label>Arquivo{editing ? " (deixe em branco para manter o atual)" : ""}</label>
          <FileDropzone
            extensions={CONTENT_EXTENSIONS}
            maxUploadMb={CONTENT_MAX_UPLOAD_MB}
            file={file}
            onFileSelected={(selected, err) => {
              setFile(selected);
              setFileError(err);
            }}
          />
          {fileError && (
            <p className="error-text">
              <Icon name="error" size={16} />
              {fileError}
            </p>
          )}
        </div>
      ) : (
        <div className="form-field">
          <label htmlFor="material-url">URL externa</label>
          <input
            id="material-url"
            type="url"
            placeholder="https://..."
            value={externalUrl}
            onChange={(e) => setExternalUrl(e.target.value)}
          />
        </div>
      )}

      <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", paddingTop: 6 }}>
        <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={isPending}>
          {isPending ? "Salvando..." : editing ? "Salvar alterações" : "Adicionar material"}
        </button>
      </div>
    </div>
  );
}
