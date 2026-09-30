import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useAnalysisStatus } from "../hooks/useAnalysisStatus";
import StatusChecklist from "../components/processing/StatusChecklist";

function useElapsedSeconds(since: string | null) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!since) return;
    const start = new Date(since).getTime();
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - start) / 1000)));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [since]);

  return elapsed;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function ProcessingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useAnalysisStatus(id!);
  const elapsed = useElapsedSeconds(data?.started_at ?? null);

  useEffect(() => {
    if (data?.status === "COMPLETED") {
      navigate(`/analyses/${id}`);
    }
  }, [data?.status, id, navigate]);

  if (isLoading || !data) {
    return <p>Carregando status...</p>;
  }

  if (data.status === "FAILED") {
    return (
      <div className="card">
        <h1>Análise em andamento</h1>
        <p className="error-text">{data.error_message ?? "A análise falhou."}</p>
        <Link to="/" className="btn btn-secondary">
          Voltar para o painel
        </Link>
      </div>
    );
  }

  return (
    <div className="card">
      <h1>Análise em andamento</h1>
      <StatusChecklist currentStatus={data.status} />
      <p>Tempo decorrido: {formatElapsed(elapsed)}</p>
      <p>
        <small>Você pode sair desta página. A análise continuará sendo processada.</small>
      </p>
    </div>
  );
}
