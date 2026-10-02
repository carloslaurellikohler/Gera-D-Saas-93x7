import { useParams } from "react-router-dom";
import Icon from "../components/ui/Icon";
import ProgressBar from "../components/ui/ProgressBar";
import TrailStatusBadge from "../components/ui/TrailStatusBadge";
import { useCompleteLearningPathItem } from "../hooks/useCompleteLearningPathItem";
import { useEnrolledLearningPaths } from "../hooks/useEnrolledLearningPaths";
import { useEnrollInLearningPath } from "../hooks/useEnrollInLearningPath";
import { useLearningPath } from "../hooks/useLearningPath";

export default function LearningPathDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const detail = useLearningPath(id);
  const enrolled = useEnrolledLearningPaths();
  const enrollMutation = useEnrollInLearningPath();
  const { complete, uncomplete } = useCompleteLearningPathItem(id);

  if (detail.isLoading) return <p className="page-subtitle">Carregando...</p>;
  if (detail.isError || !detail.data) {
    return <p className="error-text">Não foi possível carregar a trilha.</p>;
  }

  const path = detail.data;
  const isEnrolled = Boolean(enrolled.data?.some((p) => p.id === id));
  const totalItems = path.items.length;
  const completedItems = path.items.filter((item) => item.completed).length;
  const progressPercent = totalItems ? (completedItems / totalItems) * 100 : 0;
  const isCompleted = totalItems > 0 && completedItems === totalItems;

  return (
    <div>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div className="page-title-group">
          <h1>{path.title}</h1>
          {path.description && <span className="page-subtitle">{path.description}</span>}
        </div>
        {!isEnrolled && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => enrollMutation.mutate(id)}
            disabled={enrollMutation.isPending}
          >
            {enrollMutation.isPending ? "Inscrevendo..." : "Inscrever-se"}
          </button>
        )}
      </div>

      {isEnrolled && (
        <div style={{ margin: "20px 0", display: "flex", alignItems: "center", gap: 12 }}>
          <TrailStatusBadge status={isCompleted ? "COMPLETED" : "IN_PROGRESS"} />
          <div style={{ flex: 1 }}>
            <ProgressBar percent={progressPercent} />
          </div>
          <span className="page-subtitle" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
            {completedItems}/{totalItems} concluídos
          </span>
        </div>
      )}

      <div className="card" style={{ padding: 0, marginTop: 20 }}>
        {path.items.map((item, index) => (
          <div
            key={item.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              padding: "16px 20px",
              borderBottom: index < path.items.length - 1 ? "1px solid var(--border-secondary)" : "none",
            }}
          >
            <Icon
              name={item.completed ? "check_circle" : "radio_button_unchecked"}
              size={24}
              filled={item.completed}
              color={item.completed ? "var(--positive-dark)" : "var(--content-disabled)"}
            />
            <div style={{ flex: 1 }}>
              <b style={{ fontFamily: "var(--font-brand)", color: "var(--gerad-navy)" }}>
                {item.content.title}
              </b>
              {item.content.description && (
                <div className="page-subtitle" style={{ fontSize: 13 }}>
                  {item.content.description}
                </div>
              )}
            </div>
            <a
              className="btn btn-secondary"
              style={{ height: 40 }}
              href={item.content.kind === "LINK" ? item.content.external_url! : `${item.content.file_path}`}
              target="_blank"
              rel="noreferrer"
            >
              Abrir
            </a>
            {isEnrolled && (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ height: 40 }}
                onClick={() =>
                  item.completed ? uncomplete.mutate(item.id) : complete.mutate(item.id)
                }
                disabled={complete.isPending || uncomplete.isPending}
              >
                {item.completed ? "Desmarcar conclusão" : "Marcar como concluído"}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
