import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { useContentLibrary } from "../../hooks/useContentLibrary";
import { useCreateLearningPath } from "../../hooks/useCreateLearningPath";
import { useLearningPath } from "../../hooks/useLearningPath";
import { useUpdateLearningPath } from "../../hooks/useUpdateLearningPath";
import type { CriterionKey } from "../../types/content";
import type { LearningPathSummary } from "../../types/learningPath";
import ErrorBanner from "../ui/ErrorBanner";

const CRITERION_LABELS: Record<CriterionKey, string> = {
  posicionamento: "Posicionamento",
  conexao: "Conexão",
  sondagem: "Sondagem",
  direcionamento: "Direcionamento",
  encaminhamento: "Encaminhamento",
  eficiencia_conducao: "Eficiência da condução",
};

const CRITERION_OPTIONS = Object.entries(CRITERION_LABELS) as [CriterionKey, string][];

export default function TrailForm({ onDone, editing }: { onDone: () => void; editing?: LearningPathSummary }) {
  const content = useContentLibrary();
  const createPath = useCreateLearningPath();
  const updatePath = useUpdateLearningPath();
  const editingDetail = useLearningPath(editing?.id ?? "");

  const [title, setTitle] = useState(editing?.title ?? "");
  const [criterionKey, setCriterionKey] = useState<CriterionKey | "">(editing?.criterion_key ?? "");
  const [selectedContentIds, setSelectedContentIds] = useState<string[]>([]);
  const [itemsLoaded, setItemsLoaded] = useState(!editing);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editing && editingDetail.data && !itemsLoaded) {
      const sortedItems = [...editingDetail.data.items].sort((a, b) => a.order_index - b.order_index);
      setSelectedContentIds(sortedItems.map((item) => item.content.id));
      setItemsLoaded(true);
    }
  }, [editing, editingDetail.data, itemsLoaded]);

  const toggleContent = (contentId: string) => {
    setSelectedContentIds((current) =>
      current.includes(contentId) ? current.filter((id) => id !== contentId) : [...current, contentId],
    );
  };

  const isPending = editing ? updatePath.isPending : createPath.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (!title.trim()) {
      setError("Informe um título para a trilha.");
      return;
    }
    const payload = {
      title,
      criterion_key: criterionKey || undefined,
      items: selectedContentIds.map((contentId, index) => ({ content_id: contentId, order_index: index })),
    };
    try {
      if (editing) {
        await updatePath.mutateAsync({ id: editing.id, payload });
      } else {
        await createPath.mutateAsync(payload);
      }
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Erro ao ${editing ? "salvar" : "criar"} trilha.`);
    }
  };

  return (
    <div>
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
        <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={isPending}>
          {isPending ? "Salvando..." : editing ? "Salvar alterações" : "Criar trilha"}
        </button>
      </div>
    </div>
  );
}
