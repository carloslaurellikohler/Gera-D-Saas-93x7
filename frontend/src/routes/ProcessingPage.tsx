import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useAnalysisStatus } from "../hooks/useAnalysisStatus";
import StatusChecklist from "../components/processing/StatusChecklist";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";

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
    return <p className="page-subtitle">Carregando status...</p>;
  }

  if (data.status === "FAILED") {
    return (
      <div>
        <div className="page-title-group" style={{ marginBottom: 20 }}>
          <h1>Não foi possível concluir a análise</h1>
        </div>
        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, textAlign: "center", padding: 40 }}>
          <span className="access-denied-icon">
            <Icon name="sync_problem" size={36} color="var(--gray-900)" />
          </span>
          <ErrorBanner>{data.error_message ?? "A análise falhou."}</ErrorBanner>
          <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
            <Link to="/" className="btn btn-secondary">
              Voltar para o painel
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 320px", gap: 24, alignContent: "start" }}>
      <div style={{ gridColumn: "1 / 3" }} className="page-title-group">
        <span className="page-breadcrumb">Análises › Acompanhamento</span>
        <h1>Estamos analisando a conversa</h1>
      </div>

      <div className="card" style={{ padding: 32 }}>
        <StatusChecklist currentStatus={data.status} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="info-banner">
          <Icon name="schedule" size={22} color="var(--gerad-navy)" />
          <span>
            Costuma levar entre 1 e 5 minutos. Esta página se atualiza sozinha e você pode sair sem
            interromper a análise.
          </span>
        </div>
        <p className="page-subtitle">Tempo decorrido: {formatElapsed(elapsed)}</p>
        <Link to="/" className="btn btn-secondary">
          <Icon name="arrow_back" size={20} />
          Voltar ao dashboard
        </Link>
      </div>
    </div>
  );
}
