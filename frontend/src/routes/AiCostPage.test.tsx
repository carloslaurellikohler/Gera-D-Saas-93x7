import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AiCostPage from "./AiCostPage";
import { ConfirmProvider } from "../context/ConfirmContext";
import * as aiCostsApi from "../api/aiCosts";
import type {
  AiCostSummary,
  AiModelPrice,
  AiUnpricedModel,
  AiUsageEventPage,
} from "../types/aiCost";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfirmProvider>
        <MemoryRouter>
          <AiCostPage />
        </MemoryRouter>
      </ConfirmProvider>
    </QueryClientProvider>,
  );
}

const SUMMARY: AiCostSummary = {
  period: "30d",
  trend_bucket: "day",
  tracking_started_at: "2026-10-01T12:00:00Z",
  usd_to_brl_rate: 5.4,
  has_placeholder_prices: false,
  kpis: {
    total_usd: 12.34,
    events: 48,
    analyses_with_cost: 6,
    avg_usd_per_analysis: 1.85,
    assistant_messages: 10,
    avg_usd_per_assistant_message: 0.012,
    retry_usd: 0.9,
    retry_events: 2,
    input_tokens: 1_200_000,
    output_tokens: 95_000,
    cached_input_tokens: 40_000,
    reasoning_tokens: 12_000,
    audio_minutes: 73,
    unpriced_events: 0,
    no_units_events: 1,
    failed_calls: 1,
  },
  by_feature: [
    { key: "ANALYSIS", label: "Análises", total_usd: 12.2, events: 38, pct: "99%", unpriced_events: 0 },
    { key: "ASSISTANT", label: "Assistente de IA", total_usd: 0.14, events: 10, pct: "1%", unpriced_events: 0 },
  ],
  by_operation: [
    { key: "CHAT", label: "Chat (análise e assistente)", total_usd: 11.9, events: 40, pct: "96%", unpriced_events: 0 },
    { key: "TRANSCRIPTION", label: "Transcrição de áudio", total_usd: 0.44, events: 6, pct: "4%", unpriced_events: 0 },
  ],
  by_model: [
    { key: "gpt-6-sol", label: "gpt-6-sol", total_usd: 11.8, events: 36, pct: "96%", unpriced_events: 0 },
    { key: "whisper-1", label: "whisper-1", total_usd: 0.44, events: 6, pct: "4%", unpriced_events: 0 },
  ],
  by_stage: [
    { key: "TRAINING", label: "T&D e avaliação final", total_usd: 4.2, events: 6, pct: "34%", unpriced_events: 0 },
    { key: "FACT_EXTRACTION", label: "Extração factual", total_usd: 2.1, events: 6, pct: "17%", unpriced_events: 0 },
  ],
  trend: [{ period_start: "2026-10-07", total_usd: 12.34, events: 48 }],
  trend_by_feature: [
    { period_start: "2026-10-07", analysis_usd: 12.2, assistant_usd: 0.14, ingestion_usd: 0 },
  ],
  top_users: [
    {
      user_id: "u1",
      name: "Colaborador Bruno",
      role: "COLABORADOR",
      manager_name: "Gestora Ana",
      total_usd: 9.5,
      events: 30,
      analyses: 4,
    },
  ],
  top_analyses: [
    {
      analysis_id: "a1",
      participant_name: "PB Caro",
      owner_name: "Colaborador Bruno",
      input_type: "mp3",
      created_at: "2026-10-07T10:00:00Z",
      attempts: 1,
      total_usd: 3.4,
      events: 9,
    },
  ],
  budget: {
    month: "2026-10-01",
    amount_usd: 20,
    spent_usd: 8.75,
    pct: 43.75,
    warn_threshold_pct: 80,
    status: "ok",
    projected_month_end_usd: 47.8,
  },
};

const EVENTS: AiUsageEventPage = {
  items: [
    {
      id: "e1",
      occurred_at: "2026-10-07T10:00:00Z",
      feature: "ANALYSIS",
      operation: "CHAT",
      stage: "TRAINING",
      stage_label: "T&D e avaliação final",
      model: "gpt-6-sol",
      user_id: "u1",
      user_name: "Colaborador Bruno",
      analysis_id: "a1",
      participant_name: "PB Caro",
      attempt: 0,
      calls: 1,
      input_tokens: 32000,
      output_tokens: 1800,
      cached_input_tokens: 0,
      audio_seconds: null,
      cost_usd: 0.0784,
      cost_status: "PRICED",
      tokens_estimated: false,
      latency_ms: 4200,
      error_type: null,
    },
    {
      id: "e2",
      occurred_at: "2026-10-07T09:58:00Z",
      feature: "ANALYSIS",
      operation: "CHAT",
      stage: "PB_CONTEXT",
      stage_label: "Contexto do PB",
      model: "gpt-6-sol",
      user_id: "u1",
      user_name: "Colaborador Bruno",
      analysis_id: "a1",
      participant_name: "PB Caro",
      attempt: 0,
      calls: 1,
      input_tokens: 0,
      output_tokens: 0,
      cached_input_tokens: 0,
      audio_seconds: null,
      cost_usd: 0,
      cost_status: "NO_UNITS",
      tokens_estimated: false,
      latency_ms: 900,
      error_type: "APITimeoutError",
    },
  ],
  total: 2,
  offset: 0,
  limit: 50,
  models: ["gpt-6-sol", "whisper-1"],
};

const PRICES: AiModelPrice[] = [
  {
    id: "p1",
    model: "whisper-1",
    operation: "TRANSCRIPTION",
    valid_from: "2024-01-01",
    input_usd_per_mtok: null,
    cached_input_usd_per_mtok: null,
    output_usd_per_mtok: null,
    usd_per_minute: 0.006,
    is_placeholder: false,
    notes: null,
    is_current: true,
    updated_at: null,
  },
];

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(aiCostsApi, "getAiCostSummary").mockResolvedValue(SUMMARY);
  vi.spyOn(aiCostsApi, "listAiCostEvents").mockResolvedValue(EVENTS);
  vi.spyOn(aiCostsApi, "listAiModelPrices").mockResolvedValue(PRICES);
  vi.spyOn(aiCostsApi, "listUnpricedAiModels").mockResolvedValue([]);
  vi.spyOn(aiCostsApi, "getAiCostConfig").mockResolvedValue({
    warn_threshold_pct: 80,
    usd_to_brl_rate: 5.4,
    usd_to_brl_rate_updated_at: "2026-10-05T12:00:00Z",
    current_month: "2026-10-01",
    current_month_budget_usd: 20,
  });
});

describe("AiCostPage", () => {
  it("mostra os KPIs de custo vindos da API", async () => {
    renderPage();

    await screen.findByText("Custo total no período");
    expect(screen.getByText("US$ 12,34")).toBeInTheDocument();
    expect(screen.getByText("US$ 1,85")).toBeInTheDocument();
    // Equivalente em reais aparece ao lado, derivado da taxa manual.
    expect(screen.getByText("≈ R$ 66,64")).toBeInTheDocument();
  });

  it("destaca o custo de retentativas", async () => {
    renderPage();

    expect(await screen.findByText("US$ 0,90")).toBeInTheDocument();
    expect(screen.getByText("2 chamadas reexecutadas")).toBeInTheDocument();
  });

  it("mostra o consumo do orçamento do mês e a projeção", async () => {
    renderPage();

    expect(await screen.findByText("de US$ 20,00 (44%)")).toBeInTheDocument();
    expect(screen.getByText("Projeção de fim de mês: US$ 47,80")).toBeInTheDocument();
  });

  it("lista o ranking por usuário com o gestor", async () => {
    renderPage();

    expect(await screen.findAllByText("Colaborador Bruno")).toHaveLength(2);
    expect(screen.getByText("Gestora Ana")).toBeInTheDocument();
    expect(screen.getByText("PB Caro")).toBeInTheDocument();
  });

  it("declara a data de início da contabilização, porque não há backfill", async () => {
    renderPage();

    expect(
      await screen.findByText(/Contabilização de custo iniciada em 01\/10\/2026/),
    ).toBeInTheDocument();
  });

  it("avisa quando há chamadas sem preço cadastrado", async () => {
    vi.spyOn(aiCostsApi, "getAiCostSummary").mockResolvedValue({
      ...SUMMARY,
      kpis: { ...SUMMARY.kpis, unpriced_events: 7 },
    });

    renderPage();

    expect(await screen.findByText(/sem preço cadastrado neste/)).toBeInTheDocument();
    expect(screen.getByText("subestimado")).toBeInTheDocument();
  });

  it("oferece definir meta quando não há orçamento no mês", async () => {
    vi.spyOn(aiCostsApi, "getAiCostSummary").mockResolvedValue({
      ...SUMMARY,
      budget: { ...SUMMARY.budget, amount_usd: null, pct: null, status: "unset" },
    });

    renderPage();

    expect(await screen.findByText("Nenhuma meta definida para este mês")).toBeInTheDocument();
  });

  it("lista as chamadas na aba de eventos e marca as que não entraram no total", async () => {
    renderPage();
    await screen.findByText("Custo total no período");

    await userEvent.click(screen.getByRole("button", { name: "Chamadas" }));

    expect(await screen.findByText("T&D e avaliação final")).toBeInTheDocument();
    expect(screen.getByText("sem medição")).toBeInTheDocument();
    expect(screen.getByText("2 chamadas no período · página 1 de 1")).toBeInTheDocument();
    // Gap reportado: a linha precisa dizer a qual participante avaliado a chamada pertence.
    expect(screen.getAllByText("PB Caro").length).toBeGreaterThan(0);
  });

  it("mostra a quantidade de chamadas por participante avaliado na visão geral", async () => {
    renderPage();

    const participante = await screen.findByText("PB Caro");
    // "Chamadas" já existe como aba e como cabeçalho na tabela de usuários acima — a
    // tabela de participantes ganha mais uma ocorrência com a coluna nova.
    expect(screen.getAllByText("Chamadas").length).toBe(3);
    // top_analyses[0].events === 9, no mock acima — confere na própria linha do participante.
    expect(participante.closest(".data-table-row")).toHaveTextContent("9");
  });

  it("navega para Chamadas filtrado ao clicar no participante da visão geral", async () => {
    renderPage();
    await screen.findByText("Custo total no período");

    await userEvent.click(screen.getByRole("button", { name: "PB Caro" }));

    expect(await screen.findByText("T&D e avaliação final")).toBeInTheDocument();
    expect(screen.getByText(/Filtrado por análise:/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "limpar" }));
    expect(screen.queryByText(/Filtrado por análise:/)).not.toBeInTheDocument();
  });

  it("lista os preços por vigência na aba de preços", async () => {
    renderPage();
    await screen.findByText("Custo total no período");

    await userEvent.click(screen.getByRole("button", { name: "Preços e orçamento" }));

    expect(await screen.findByText("whisper-1")).toBeInTheDocument();
    expect(screen.getByText("vigente")).toBeInTheDocument();
    expect(screen.getByLabelText("Meta do mês (US$)")).toHaveValue(20);
  });

  it("mostra erro quando a API falha", async () => {
    vi.spyOn(aiCostsApi, "getAiCostSummary").mockRejectedValue(new Error("falhou"));

    renderPage();

    expect(
      await screen.findByText("Não foi possível carregar os indicadores de custo."),
    ).toBeInTheDocument();
  });
  it("marca o modelo sem preço em vez de mostrar US$ 0 ambíguo", async () => {
    vi.spyOn(aiCostsApi, "getAiCostSummary").mockResolvedValue({
      ...SUMMARY,
      by_model: [
        { key: "gpt-6-sol", label: "gpt-6-sol", total_usd: 11.8, events: 36, pct: "100%", unpriced_events: 0 },
        { key: "gpt-6-luna", label: "gpt-6-luna", total_usd: 0, events: 4, pct: "0%", unpriced_events: 4 },
      ],
    });

    renderPage();

    expect(await screen.findByText("sem preço")).toBeInTheDocument();
    // "não apurado" deixa explícito que não é custo zero, é custo desconhecido.
    expect(screen.getByText("não apurado")).toBeInTheDocument();
  });

  it("lista os modelos em uso sem preço com o nome exato reportado pela API", async () => {
    const pendentes: AiUnpricedModel[] = [
      {
        model: "gpt-6-sol-2026-05-01",
        operation: "CHAT",
        events: 12,
        first_seen: "2026-10-05T10:00:00Z",
        last_seen: "2026-10-07T18:00:00Z",
      },
    ];
    vi.spyOn(aiCostsApi, "listUnpricedAiModels").mockResolvedValue(pendentes);

    renderPage();
    await screen.findByText("Custo total no período");
    await userEvent.click(screen.getByRole("button", { name: "Preços e orçamento" }));

    expect(await screen.findByText("Modelos em uso sem preço cadastrado")).toBeInTheDocument();
    // O snapshot datado, que é o que precisa ser cadastrado — não o nome do .env.
    expect(screen.getByText("gpt-6-sol-2026-05-01")).toBeInTheDocument();
    expect(screen.getByText(/12 chamadas · última em 07\/10\/2026/)).toBeInTheDocument();
  });

  it("pré-preenche o formulário com o nome exato do modelo pendente", async () => {
    vi.spyOn(aiCostsApi, "listUnpricedAiModels").mockResolvedValue([
      {
        model: "gpt-6-sol-2026-05-01",
        operation: "CHAT",
        events: 12,
        first_seen: "2026-10-05T10:00:00Z",
        last_seen: "2026-10-07T18:00:00Z",
      },
    ]);

    renderPage();
    await screen.findByText("Custo total no período");
    await userEvent.click(screen.getByRole("button", { name: "Preços e orçamento" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Cadastrar preço de gpt-6-sol-2026-05-01" }),
    );

    expect(await screen.findByLabelText("Modelo")).toHaveValue("gpt-6-sol-2026-05-01");
  });

  it("não mostra a seção de pendências quando todo modelo tem preço", async () => {
    renderPage();
    await screen.findByText("Custo total no período");
    await userEvent.click(screen.getByRole("button", { name: "Preços e orçamento" }));

    await screen.findByText("whisper-1");
    expect(screen.queryByText("Modelos em uso sem preço cadastrado")).not.toBeInTheDocument();
  });
});
