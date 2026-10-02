import { Link } from "react-router-dom";
import { useEnrolledLearningPaths } from "../../hooks/useEnrolledLearningPaths";
import EmptyState from "../ui/EmptyState";
import ProgressBar from "../ui/ProgressBar";
import TrailStatusBadge from "../ui/TrailStatusBadge";
import type { EnrolledLearningPathSummary } from "../../types/learningPath";

export default function InProgressTab() {
  const enrolled = useEnrolledLearningPaths();

  if (enrolled.isLoading) return <p className="page-subtitle">Carregando...</p>;
  if (enrolled.isError) return <p className="error-text">Não foi possível carregar suas trilhas.</p>;

  const paths = enrolled.data ?? [];
  if (paths.length === 0) {
    return (
      <EmptyState
        icon="school"
        title="Você ainda não se inscreveu em nenhuma trilha"
        description="Inscreva-se em uma trilha na aba 'Trilhas sugeridas' para acompanhar seu progresso aqui."
      />
    );
  }

  const inProgress = paths.filter((p) => !p.is_completed);
  const completed = paths.filter((p) => p.is_completed);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <TrailGroup title="Em andamento" paths={inProgress} />
      <TrailGroup title="Concluídas" paths={completed} />
    </div>
  );
}

function TrailGroup({ title, paths }: { title: string; paths: EnrolledLearningPathSummary[] }) {
  if (paths.length === 0) return null;
  return (
    <div>
      <h3 style={{ marginBottom: 12 }}>{title}</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
        {paths.map((path) => (
          <Link
            key={path.id}
            to={`/biblioteca/trilhas/${path.id}`}
            className="card"
            style={{ display: "flex", flexDirection: "column", gap: 10, color: "inherit", textDecoration: "none" }}
          >
            <TrailStatusBadge status={path.is_completed ? "COMPLETED" : "IN_PROGRESS"} />
            <b style={{ fontFamily: "var(--font-brand)", fontSize: 16, color: "var(--gerad-navy)" }}>
              {path.title}
            </b>
            <ProgressBar percent={path.progress_percent} />
            <span className="page-subtitle" style={{ fontSize: 12 }}>
              {path.completed_count}/{path.item_count} materiais concluídos
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
