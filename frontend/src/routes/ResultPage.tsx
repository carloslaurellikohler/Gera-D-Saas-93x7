import { useState } from "react";
import { useParams, Navigate } from "react-router-dom";
import { useAnalysis, useAnalysisResult, useTranscription } from "../hooks/useAnalysis";
import SummaryTab from "../components/results/SummaryTab";
import AnalysisTab from "../components/results/AnalysisTab";
import ReportTab from "../components/results/ReportTab";
import TranscriptionTab from "../components/results/TranscriptionTab";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { formatDurationSeconds } from "../lib/format";

type TabKey = "resumo" | "analise" | "relatorio" | "transcricao";

const TABS: { key: TabKey; label: string }[] = [
  { key: "resumo", label: "Resumo" },
  { key: "analise", label: "Análise" },
  { key: "relatorio", label: "Relatório" },
  { key: "transcricao", label: "Transcrição" },
];

export default function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<TabKey>("resumo");
  const { data: analysis, isLoading } = useAnalysis(id!);

  const isCompleted = analysis?.status === "COMPLETED";
  const { data: resultData, isLoading: resultLoading } = useAnalysisResult(id!, isCompleted);
  const { data: transcriptionData, isLoading: transcriptionLoading } = useTranscription(
    id!,
    activeTab === "transcricao",
  );

  if (isLoading || !analysis) {
    return <p className="page-subtitle">Carregando...</p>;
  }

  if (analysis.status !== "COMPLETED" && analysis.status !== "FAILED") {
    return <Navigate to={`/analyses/${id}/processing`} replace />;
  }

  if (analysis.status === "FAILED") {
    return (
      <div>
        <h1>{analysis.participant_name}</h1>
        <div style={{ marginTop: 16 }}>
          <ErrorBanner>{analysis.error_message ?? "A análise falhou."}</ErrorBanner>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <span className="page-breadcrumb">Análises › {analysis.participant_name}</span>
          <h1>{analysis.objective}</h1>
          <span className="page-subtitle">
            {analysis.participant_name} · {formatDurationSeconds(analysis.duration_seconds)} ·
            Metodologia 93x7®
          </span>
        </div>
        <button className="btn btn-primary" onClick={() => setActiveTab("relatorio")}>
          <Icon name="download" size={20} />
          Relatório executivo
        </button>
      </div>

      <div className="tabs" style={{ margin: "20px 0" }}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={activeTab === tab.key ? "active" : ""}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "resumo" && (
        <SummaryTab
          analysis={analysis}
          result={resultData?.analysis_result ?? null}
          resultLoading={resultLoading}
        />
      )}
      {activeTab === "analise" && (
        <AnalysisTab result={resultData?.analysis_result ?? null} loading={resultLoading} />
      )}
      {activeTab === "relatorio" && <ReportTab analysisId={analysis.id} />}
      {activeTab === "transcricao" && (
        <TranscriptionTab
          transcription={transcriptionData?.transcription ?? null}
          loading={transcriptionLoading}
        />
      )}
    </div>
  );
}
