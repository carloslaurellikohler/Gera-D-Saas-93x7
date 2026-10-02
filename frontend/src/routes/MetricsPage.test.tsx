import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MetricsPage from "./MetricsPage";
import * as metricsApi from "../api/metrics";
import type { MetricsEvolutionResponse } from "../types/metrics";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MetricsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const EVOLUTION: MetricsEvolutionResponse = {
  period: "90d",
  radar: [
    { key: "posicionamento", label: "Posicionamento", score: 8.2, previous_score: 7.0, sample_size: 4 },
    { key: "conexao", label: "Conexão", score: 7.5, previous_score: 6.8, sample_size: 4 },
    { key: "sondagem", label: "Sondagem", score: 6.9, previous_score: 6.5, sample_size: 4 },
    { key: "direcionamento", label: "Direcionamento", score: 7.1, previous_score: 6.9, sample_size: 4 },
    { key: "encaminhamento", label: "Encaminhamento", score: 8.0, previous_score: 7.4, sample_size: 4 },
    { key: "eficiencia_conducao", label: "Eficiência na condução", score: 7.3, previous_score: 7.0, sample_size: 4 },
  ],
  trend: [
    { period_start: "2026-01-05", count: 4, avg_overall_score: 7.6, avg_pilar_93: 7.8, avg_pilar_7: 7.1 },
  ],
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("MetricsPage", () => {
  it("renders both chart cards when the API returns data", async () => {
    vi.spyOn(metricsApi, "getMetricsEvolution").mockResolvedValue(EVOLUTION);

    renderPage();

    expect(await screen.findByText("Evolução temporal")).toBeInTheDocument();
    expect(screen.getByText("Comparação por critério")).toBeInTheDocument();
  });

  it("shows empty states for both charts when there are no completed analyses", async () => {
    vi.spyOn(metricsApi, "getMetricsEvolution").mockResolvedValue({
      period: "90d",
      radar: EVOLUTION.radar.map((r) => ({ ...r, score: null, previous_score: null, sample_size: 0 })),
      trend: [],
    });

    renderPage();

    expect((await screen.findAllByText(/Sem análises concluídas no período/i)).length).toBeGreaterThan(0);
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(metricsApi, "getMetricsEvolution").mockRejectedValue(new Error("boom"));

    renderPage();

    expect(await screen.findByText("Não foi possível carregar os indicadores.")).toBeInTheDocument();
  });
});
