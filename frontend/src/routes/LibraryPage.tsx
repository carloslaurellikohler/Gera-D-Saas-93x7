import { useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useConfirm } from "../context/ConfirmContext";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import Modal from "../components/ui/Modal";
import InProgressTab from "../components/library/InProgressTab";
import MaterialForm from "../components/library/MaterialForm";
import TrailForm from "../components/library/TrailForm";
import { useContentLibrary } from "../hooks/useContentLibrary";
import { useDeleteContent } from "../hooks/useDeleteContent";
import { useDeleteLearningPath } from "../hooks/useDeleteLearningPath";
import { useLearningPaths } from "../hooks/useLearningPaths";
import { useRecommendedPaths } from "../hooks/useRecommendedPaths";
import { ApiError } from "../api/client";
import type { ContentResponse, CriterionKey } from "../types/content";
import type { LearningPathSummary } from "../types/learningPath";

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
      {tab === "andamento" && <InProgressTab />}
    </div>
  );
}

type TrailFormMode = { mode: "create" } | { mode: "edit"; path: LearningPathSummary };

function TrailsTab({ isAdmin }: { isAdmin: boolean }) {
  const [formMode, setFormMode] = useState<TrailFormMode | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const confirm = useConfirm();
  const recommended = useRecommendedPaths();
  const paths = useLearningPaths();
  const deleteTrail = useDeleteLearningPath();

  const handleDelete = async (path: LearningPathSummary) => {
    const confirmed = await confirm({
      title: `Excluir a trilha "${path.title}"?`,
      description: "Esta ação não pode ser desfeita.",
      confirmLabel: "Excluir",
      tone: "danger",
    });
    if (!confirmed) {
      return;
    }
    setActionError(null);
    try {
      await deleteTrail.mutateAsync(path.id);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Erro ao excluir trilha.");
    }
  };

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
          <button type="button" className="btn btn-secondary" onClick={() => setFormMode({ mode: "create" })}>
            Nova trilha
          </button>
        </div>
      )}
      {isAdmin && actionError && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner>{actionError}</ErrorBanner>
        </div>
      )}
      {isAdmin && (
        <Modal
          open={formMode !== null}
          title={formMode?.mode === "edit" ? "Editar trilha" : "Nova trilha"}
          onClose={() => setFormMode(null)}
          size="large"
        >
          <TrailForm
            onDone={() => setFormMode(null)}
            editing={formMode?.mode === "edit" ? formMode.path : undefined}
          />
        </Modal>
      )}

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
            <Link
              key={path.id}
              to={`/biblioteca/trilhas/${path.id}`}
              className="card"
              style={{ position: "relative", padding: 0, overflow: "hidden", color: "inherit", textDecoration: "none" }}
            >
              {isAdmin && (
                <div style={{ position: "absolute", top: 8, right: 8, display: "flex", gap: 4, zIndex: 1 }}>
                  <button
                    type="button"
                    title="Editar trilha"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setFormMode({ mode: "edit", path });
                    }}
                    style={cardActionButtonStyle}
                  >
                    <Icon name="edit" size={18} color="var(--gerad-navy)" />
                  </button>
                  <button
                    type="button"
                    title="Excluir trilha"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      void handleDelete(path);
                    }}
                    style={cardActionButtonStyle}
                  >
                    <Icon name="delete" size={18} color="var(--gerad-navy)" />
                  </button>
                </div>
              )}
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
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

const cardActionButtonStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: 32,
  height: 32,
  borderRadius: "50%",
  border: "1px solid var(--border-secondary)",
  background: "var(--background-primary)",
  cursor: "pointer",
};

type MaterialFormMode = { mode: "create" } | { mode: "edit"; item: ContentResponse };

function MaterialsTab({ isAdmin }: { isAdmin: boolean }) {
  const [formMode, setFormMode] = useState<MaterialFormMode | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const confirm = useConfirm();
  const content = useContentLibrary();
  const deleteMaterial = useDeleteContent();

  const handleDelete = async (item: ContentResponse) => {
    const confirmed = await confirm({
      title: `Excluir o material "${item.title}"?`,
      description: "Esta ação não pode ser desfeita.",
      confirmLabel: "Excluir",
      tone: "danger",
    });
    if (!confirmed) {
      return;
    }
    setActionError(null);
    try {
      await deleteMaterial.mutateAsync(item.id);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Erro ao excluir material.");
    }
  };

  return (
    <>
      {isAdmin && (
        <div style={{ marginBottom: 16 }}>
          <button type="button" className="btn btn-secondary" onClick={() => setFormMode({ mode: "create" })}>
            Adicionar material
          </button>
        </div>
      )}
      {isAdmin && actionError && (
        <div style={{ marginBottom: 16 }}>
          <ErrorBanner>{actionError}</ErrorBanner>
        </div>
      )}
      {isAdmin && (
        <Modal
          open={formMode !== null}
          title={formMode?.mode === "edit" ? "Editar material" : "Adicionar material"}
          onClose={() => setFormMode(null)}
        >
          <MaterialForm
            onDone={() => setFormMode(null)}
            editing={formMode?.mode === "edit" ? formMode.item : undefined}
          />
        </Modal>
      )}

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
            <div
              key={item.id}
              className="card"
              style={{ position: "relative", display: "flex", flexDirection: "column", gap: 10 }}
            >
              {isAdmin && (
                <div style={{ position: "absolute", top: 12, right: 12, display: "flex", gap: 4 }}>
                  <button
                    type="button"
                    title="Editar material"
                    onClick={() => setFormMode({ mode: "edit", item })}
                    style={cardActionButtonStyle}
                  >
                    <Icon name="edit" size={18} color="var(--gerad-navy)" />
                  </button>
                  <button
                    type="button"
                    title="Excluir material"
                    onClick={() => void handleDelete(item)}
                    style={cardActionButtonStyle}
                  >
                    <Icon name="delete" size={18} color="var(--gerad-navy)" />
                  </button>
                </div>
              )}
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
