import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import FileDropzone from "../components/forms/FileDropzone";
import { useContentLibrary } from "../hooks/useContentLibrary";
import { useCreateContent } from "../hooks/useCreateContent";
import { useCreateLearningPath } from "../hooks/useCreateLearningPath";
import { useLearningPaths } from "../hooks/useLearningPaths";
import { useRecommendedPaths } from "../hooks/useRecommendedPaths";
import { CONTENT_EXTENSIONS, CONTENT_MAX_UPLOAD_MB } from "../lib/contentUploadConstraints";
import { ApiError } from "../api/client";
import type { ContentKind, CriterionKey } from "../types/content";

type LibraryTab = "trilhas" | "materiais" | "andamento";

const TABS: { key: LibraryTab; label: string }[] = [
  { key: "trilhas", label: "Trilhas sugeridas" },
  { key: "materiais", label: "Materiais de apoio" },
  { key: "andamento", label: "Em andamento" },
];

const CRITERION_LABELS: Record<CriterionKey, string> = {
  posicionamento: "Posicionamento",
  conexao: "Conexão",
  sondagem: "Sondagem",
  direcionamento: "Direcionamento",
  encaminhamento: "Encaminhamento",
  eficiencia_conducao: "Eficiência da condução",
};

const CRITERION_OPTIONS = Object.entries(CRITERION_LABELS) as [CriterionKey, string][];

export default function LibraryPage() {
  const [tab, setTab] = useState<LibraryTab>("trilhas");
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  return (
    <div>
      <div className="page-title-group">
        <h1>Biblioteca</h1>
        <span className="page-subtitle">Materiais e trilhas sugeridos a partir dos seus resultados.</span>
      </div>

      <div className="tabs" style={{ margin: "20px 0" }}>
        {TABS.map((t) => (
          <button key={t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "trilhas" && <TrailsTab isAdmin={isAdmin} />}
      {tab === "materiais" && <MaterialsTab isAdmin={isAdmin} />}
      {tab === "andamento" && <p className="page-subtitle">Você ainda não iniciou nenhuma trilha.</p>}
    </div>
  );
}

function TrailsTab({ isAdmin }: { isAdmin: boolean }) {
  const [showForm, setShowForm] = useState(false);
  const recommended = useRecommendedPaths();
  const paths = useLearningPaths();

  return (
    <>
      {(recommended.data?.length ?? 0) > 0 && (
        <div className="info-banner" style={{ marginBottom: 16 }}>
          <Icon name="auto_awesome" size={22} />
          <span>
            Sugestões baseadas nas suas análises recentes:{" "}
            {recommended.data!.map((path, index) => (
              <span key={path.id}>
                <b>{path.title}</b>
                {index < recommended.data!.length - 1 ? ", " : ""}
              </span>
            ))}
            .
          </span>
        </div>
      )}

      {isAdmin && (
        <div style={{ marginBottom: 16 }}>
          <button type="button" className="btn btn-secondary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancelar" : "Nova trilha"}
          </button>
        </div>
      )}
      {isAdmin && showForm && <NewTrailForm onDone={() => setShowForm(false)} />}

      {paths.isLoading && <p className="page-subtitle">Carregando...</p>}
      {paths.isError && <p className="error-text">Não foi possível carregar as trilhas.</p>}

      {paths.data && paths.data.length === 0 && (
        <EmptyState
          icon="school"
          title="Nenhuma trilha cadastrada ainda"
          description="Quando houver trilhas de treinamento cadastradas, elas aparecem aqui."
        />
      )}

      {paths.data && paths.data.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
          {paths.data.map((path) => (
            <div key={path.id} className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div
                style={{
                  height: 120,
                  background: "var(--background-brand-secondary-n5)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon name="school" size={48} color="var(--gerad-navy)" />
              </div>
              <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                {path.criterion_key && (
                  <span className="pill" style={{ alignSelf: "flex-start", height: "auto", padding: "3px 10px" }}>
                    {CRITERION_LABELS[path.criterion_key]}
                  </span>
                )}
                <b style={{ fontFamily: "var(--font-brand)", fontSize: 17, color: "var(--gerad-navy)" }}>
                  {path.title}
                </b>
                <span className="page-subtitle" style={{ fontSize: 12 }}>
                  {path.item_count} {path.item_count === 1 ? "módulo" : "módulos"}
                  {path.estimated_duration_minutes ? ` · ${path.estimated_duration_minutes} min` : ""}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function NewTrailForm({ onDone }: { onDone: () => void }) {
  const content = useContentLibrary();
  const createPath = useCreateLearningPath();

  const [title, setTitle] = useState("");
  const [criterionKey, setCriterionKey] = useState<CriterionKey | "">("");
  const [selectedContentIds, setSelectedContentIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const toggleContent = (contentId: string) => {
    setSelectedContentIds((current) =>
      current.includes(contentId) ? current.filter((id) => id !== contentId) : [...current, contentId],
    );
  };

  const handleSubmit = async () => {
    setError(null);
    if (!title.trim()) {
      setError("Informe um título para a trilha.");
      return;
    }
    try {
      await createPath.mutateAsync({
        title,
        criterion_key: criterionKey || undefined,
        items: selectedContentIds.map((contentId, index) => ({ content_id: contentId, order_index: index })),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar trilha.");
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="form-field" style={{ marginTop: error ? 18 : 0 }}>
        <label htmlFor="trail-title">Título da trilha</label>
        <input id="trail-title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>

      <div className="form-field">
        <label htmlFor="trail-criterion">Critério associado</label>
        <select
          id="trail-criterion"
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
        <label>Materiais (na ordem desejada)</label>
        {content.data && content.data.length === 0 && (
          <span className="page-subtitle">Cadastre materiais na aba "Materiais de apoio" primeiro.</span>
        )}
        {content.data && content.data.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {content.data.map((item) => (
              <label key={item.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="checkbox"
                  checked={selectedContentIds.includes(item.id)}
                  onChange={() => toggleContent(item.id)}
                />
                {item.title}
              </label>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", paddingTop: 6 }}>
        <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={createPath.isPending}>
          {createPath.isPending ? "Criando..." : "Criar trilha"}
        </button>
      </div>
    </div>
  );
}

function MaterialsTab({ isAdmin }: { isAdmin: boolean }) {
  const [showForm, setShowForm] = useState(false);
  const content = useContentLibrary();

  return (
    <>
      {isAdmin && (
        <div style={{ marginBottom: 16 }}>
          <button type="button" className="btn btn-secondary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancelar" : "Adicionar material"}
          </button>
        </div>
      )}
      {isAdmin && showForm && <NewMaterialForm onDone={() => setShowForm(false)} />}

      {content.isLoading && <p className="page-subtitle">Carregando...</p>}
      {content.isError && <p className="error-text">Não foi possível carregar os materiais.</p>}

      {content.data && content.data.length === 0 && (
        <EmptyState
          icon="menu_book"
          title="Nenhum material de apoio disponível ainda"
          description="Materiais cadastrados pela administração aparecem aqui."
        />
      )}

      {content.data && content.data.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
          {content.data.map((item) => (
            <div key={item.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <Icon name={item.kind === "FILE" ? "description" : "link"} size={28} color="var(--gerad-navy)" />
              {item.criterion_key && (
                <span className="pill" style={{ alignSelf: "flex-start", height: "auto", padding: "3px 10px" }}>
                  {CRITERION_LABELS[item.criterion_key]}
                </span>
              )}
              <b style={{ fontFamily: "var(--font-brand)", fontSize: 16, color: "var(--gerad-navy)" }}>
                {item.title}
              </b>
              {item.description && <span className="page-subtitle">{item.description}</span>}
              <a
                className="btn btn-secondary"
                style={{ height: 40, textAlign: "center" }}
                href={item.kind === "LINK" ? item.external_url! : `${item.file_path}`}
                target="_blank"
                rel="noreferrer"
              >
                Abrir
              </a>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function NewMaterialForm({ onDone }: { onDone: () => void }) {
  const createContent = useCreateContent();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [criterionKey, setCriterionKey] = useState<CriterionKey | "">("");
  const [kind, setKind] = useState<ContentKind>("LINK");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [externalUrl, setExternalUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    if (!title.trim()) {
      setError("Informe um título para o material.");
      return;
    }
    if (kind === "FILE" && !file) {
      setError("Selecione um arquivo PDF.");
      return;
    }
    if (kind === "LINK" && !externalUrl.trim()) {
      setError("Informe a URL externa.");
      return;
    }
    try {
      await createContent.mutateAsync({
        title,
        description: description || undefined,
        criterion_key: criterionKey || undefined,
        kind,
        file: kind === "FILE" ? file ?? undefined : undefined,
        external_url: kind === "LINK" ? externalUrl : undefined,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao cadastrar material.");
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16 }}>
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
          <div className="input-type-choice">
            <button type="button" className={kind === "LINK" ? "active" : ""} onClick={() => setKind("LINK")}>
              Link externo
            </button>
            <button type="button" className={kind === "FILE" ? "active" : ""} onClick={() => setKind("FILE")}>
              Arquivo PDF
            </button>
          </div>
        </div>
      </div>

      {kind === "FILE" ? (
        <div className="form-field">
          <label>Arquivo</label>
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
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={createContent.isPending}
        >
          {createContent.isPending ? "Enviando..." : "Adicionar material"}
        </button>
      </div>
    </div>
  );
}
