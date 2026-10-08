import { useState } from "react";
import CostEventsTab from "../components/aicost/CostEventsTab";
import CostOverviewTab from "../components/aicost/CostOverviewTab";
import CostSettingsTab from "../components/aicost/CostSettingsTab";
import Icon from "../components/ui/Icon";
import { useAiCostSummary } from "../hooks/useAiCostSummary";
import { formatDate } from "../lib/format";
import type { AiCostPeriod } from "../types/aiCost";

const PERIOD_LABELS: Record<AiCostPeriod, string> = {
  "7d": "Últimos 7 dias",
  "30d": "Últimos 30 dias",
  "90d": "Últimos 90 dias",
  mtd: "Mês corrente",
};

type Tab = "overview" | "events" | "settings";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Visão geral" },
  { key: "events", label: "Chamadas" },
  { key: "settings", label: "Preços e orçamento" },
];

export default function AiCostPage() {
  const [period, setPeriod] = useState<AiCostPeriod>("30d");
  const [tab, setTab] = useState<Tab>("overview");
  const { data, isLoading, isError } = useAiCostSummary(period);

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Custos de IA</h1>
          <span className="page-subtitle">
            Quanto a plataforma gasta com OpenAI, em quê e por quem.
          </span>
        </div>
        {tab !== "settings" && (
          <span className="search-field">
            <select
              aria-label="Período"
              value={period}
              onChange={(e) => setPeriod(e.target.value as AiCostPeriod)}
              style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
            >
              {(Object.keys(PERIOD_LABELS) as AiCostPeriod[]).map((key) => (
                <option key={key} value={key}>
                  {PERIOD_LABELS[key]}
                </option>
              ))}
            </select>
            <Icon name="expand_more" size={20} />
          </span>
        )}
      </div>

      <div className="tabs" style={{ marginTop: 20 }}>
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={tab === item.key ? "active" : undefined}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="page-subtitle" style={{ marginTop: 20 }}>Carregando...</p>}
      {isError && (
        <p className="error-text" style={{ marginTop: 20 }}>
          Não foi possível carregar os indicadores de custo.
        </p>
      )}

      {tab === "overview" && data && (
        <>
          <CostOverviewTab summary={data} onGoToPrices={() => setTab("settings")} />
          {/* A contabilização não tem backfill: análises anteriores à feature simplesmente
              não têm dados de token, e a tela diz isso em vez de fingir um histórico. */}
          <p className="page-subtitle" style={{ marginTop: 20, fontSize: 12 }}>
            {data.tracking_started_at
              ? `Contabilização de custo iniciada em ${formatDate(data.tracking_started_at)}. Análises anteriores a essa data não têm dados de consumo.`
              : "Nenhuma chamada de IA registrada ainda. A contabilização começa na próxima análise ou mensagem do assistente."}
            {" "}Tokens de embedding são contados localmente (tiktoken), não reportados pela API.
          </p>
        </>
      )}

      {tab === "events" && <CostEventsTab period={period} />}
      {tab === "settings" && <CostSettingsTab />}
    </div>
  );
}
