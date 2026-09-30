import { useState } from "react";
import { useParams, Navigate } from "react-router-dom";
import { useAnalysis, useAnalysisResult, useTranscription } from "../hooks/useAnalysis";
import SummaryTab from "../components/results/SummaryTab";
import AnalysisTab from "../components/results/AnalysisTab";
import ReportTab from "../components/results/ReportTab";
import TranscriptionTab from "../components/results/TranscriptionTab";

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
    return <p>Carregando...</p>;
  }

  if (analysis.status !== "COMPLETED" && analysis.status !== "FAILED") {
    return <Navigate to={`/analyses/${id}/processing`} replace />;
  }

  if (analysis.status === "FAILED") {
    return (
      <div className="card">
        <h1>{analysis.participant_name}</h1>
        <p className="error-text">{analysis.error_message ?? "A análise falhou."}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="tabs">
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
