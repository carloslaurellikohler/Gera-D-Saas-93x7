import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProcessingPage from "./ProcessingPage";
import * as analysesApi from "../api/analyses";
import type { AnalysisStatusResponse } from "../types/analysis";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "abc-123" }),
  };
});

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProcessingPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function statusResponse(overrides: Partial<AnalysisStatusResponse>): AnalysisStatusResponse {
  return {
    id: "abc-123",
    status: "ANALYZING",
    error_message: null,
    started_at: "2026-01-01T00:00:00Z",
    completed_at: null,
    updated_at: "2026-01-01T00:00:05Z",
    ...overrides,
  };
}

beforeEach(() => {
  mockNavigate.mockReset();
  vi.restoreAllMocks();
});

describe("ProcessingPage", () => {
  it("shows the checklist step matching the current status", async () => {
    vi.spyOn(analysesApi, "getAnalysisStatus").mockResolvedValue(
      statusResponse({ status: "ANALYZING" }),
    );

    renderPage();

    expect(await screen.findByText("Analisando conversa")).toBeInTheDocument();
    // etapa anterior (transcrição) já concluída
    const list = screen.getByRole("list");
    expect(list.textContent).toContain("Transcrição concluída");
    // ícone da etapa ativa deve girar, indicando processo em andamento
    expect(list.querySelector(".ui-stepper-item-active .ui-icon-spin")).not.toBeNull();
  });

  it("shows the error message and a back link when the analysis failed", async () => {
    vi.spyOn(analysesApi, "getAnalysisStatus").mockResolvedValue(
      statusResponse({ status: "FAILED", error_message: "Falha ao gerar a análise da conversa." }),
    );

    renderPage();

    expect(await screen.findByText("Falha ao gerar a análise da conversa.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para o painel" })).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("navigates to the result page once the analysis completes", async () => {
    vi.spyOn(analysesApi, "getAnalysisStatus").mockResolvedValue(
      statusResponse({ status: "COMPLETED", completed_at: "2026-01-01T00:02:00Z" }),
    );

    renderPage();

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/analyses/abc-123"));
  });

  it("stops polling once a terminal status is reached", async () => {
    const getStatus = vi
      .spyOn(analysesApi, "getAnalysisStatus")
      .mockResolvedValue(statusResponse({ status: "COMPLETED" }));

    renderPage();

    await waitFor(() => expect(getStatus).toHaveBeenCalledTimes(1));
    // aguarda um pouco além do intervalo de polling (2s) para garantir que não houve nova chamada
    await new Promise((resolve) => setTimeout(resolve, 2200));
    expect(getStatus).toHaveBeenCalledTimes(1);
  });
});
