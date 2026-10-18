import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DashboardPage from "./DashboardPage";
import * as analysesApi from "../api/analyses";
import * as authApi from "../api/auth";
import * as dashboardApi from "../api/dashboard";
import * as usersApi from "../api/users";
import { AuthProvider } from "../context/AuthContext";
import type { DashboardStatsResponse } from "../types/dashboard";
import type { PaginatedResponse, AnalysisListItem } from "../types/analysis";
import type { User } from "../types/auth";

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const COLABORADOR: User = {
  id: "colab-1",
  name: "Colaboradora Teste",
  email: "colab@example.com",
  role: "COLABORADOR",
  status: "ACTIVE",
  manager_id: null,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

const GESTOR: User = { ...COLABORADOR, id: "gestor-1", role: "GESTOR" };

const ANALYSES: PaginatedResponse<AnalysisListItem> = {
  items: [
    {
      id: "1",
      participant_name: "João Silva",
      objective: "Onboarding",
      status: "COMPLETED",
      created_at: "2026-01-01T00:00:00Z",
      owner_id: "colab-1",
      owner_name: "Colaboradora Teste",
      duration_seconds: 1800,
      overall_score: 8.5,
      overall_farol_level: "excelente",
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

const STATS: DashboardStatsResponse = {
  period: "6m",
  volume_by_status: [{ status: "COMPLETED", count: 1 }],
  farol_distribution: [{ label: "Atenção", level: "atencao", count: 1, pct: "100%" }],
  trend: [{ period_start: "2026-01-05", count: 1, avg_score: 7.2 }],
  team_board: null,
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(COLABORADOR);
  vi.spyOn(usersApi, "listMyTeam").mockResolvedValue([]);
  vi.spyOn(usersApi, "listUsers").mockResolvedValue([]);
});

describe("DashboardPage", () => {
  it("renders the personal KPI block computed from the loaded analyses", async () => {
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue({
      ...ANALYSES,
      items: [
        ANALYSES.items[0],
        { ...ANALYSES.items[0], id: "2", participant_name: "Maria Souza", overall_score: 5.5 },
      ],
      total: 2,
    });
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    expect(await screen.findByText("Minhas análises")).toBeInTheDocument();
    // Nota média vem da própria lista carregada (8.5 e 5.5), não de `stats.trend` (7.2).
    expect(screen.getByText("7.0")).toBeInTheDocument();
    expect(screen.queryByText("7.2")).not.toBeInTheDocument();
  });

  it("omits the KPI block when there is nothing to aggregate yet", async () => {
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue({
      ...STATS,
      volume_by_status: [],
      farol_distribution: [],
      trend: [],
    });

    renderPage();

    expect(await screen.findByText("Nenhuma análise ainda")).toBeInTheDocument();
    expect(screen.queryByText("Minhas análises")).not.toBeInTheDocument();
  });

  it("hides the Colaborador column and filter for a COLABORADOR but shows tempo and nota", async () => {
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    expect(screen.queryByText("Colaborador")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Filtrar por colaborador")).not.toBeInTheDocument();
    expect(screen.getByText("30 min")).toBeInTheDocument();
    // "8.5"/"Excelente" aparecem tanto na coluna Nota quanto nos cards de topo
    // (única análise carregada, então o agregado coincide com o item individual).
    expect(screen.getAllByText("8.5").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Excelente").length).toBeGreaterThan(0);
  });

  it("shows the Colaborador column with the owner name for a GESTOR", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(GESTOR);
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    expect(screen.getByText("Colaborador")).toBeInTheDocument();
    expect(screen.getByText("Colaboradora Teste")).toBeInTheDocument();
  });

  it("shows a dash in the Nota column when the analysis has no score/farol yet", async () => {
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue({
      ...ANALYSES,
      items: [{ ...ANALYSES.items[0], overall_score: null, overall_farol_level: null, duration_seconds: null }],
    });
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    expect(screen.queryByText("8.5")).not.toBeInTheDocument();
    expect(screen.queryByText("Excelente")).not.toBeInTheDocument();
  });

  it("shows the team board and team-scoped KPI labels for a GESTOR", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(GESTOR);
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue({
      ...STATS,
      team_board: [
        { user_id: "colab-1", name: "Colaboradora Teste", count: 2, avg_score: 7.5, level: "atencao", trend: "up" },
      ],
    });

    renderPage();

    expect(await screen.findByText("Análises da equipe")).toBeInTheDocument();
    expect(screen.getByText("Quadro da equipe")).toBeInTheDocument();
    // Aparece duas vezes: no "Quadro da equipe" (agregado) e na coluna Colaborador
    // da tabela de análises (mesmo colaborador dono da análise do fixture ANALYSES).
    expect(screen.getAllByText("Colaboradora Teste").length).toBeGreaterThan(0);
  });

  it("lets a GESTOR filter the list by colaborador", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(GESTOR);
    vi.spyOn(usersApi, "listMyTeam").mockResolvedValue([
      { ...COLABORADOR, id: "colab-1", name: "Colaboradora Teste" },
    ]);
    const listAnalysesSpy = vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    const select = await screen.findByLabelText("Filtrar por colaborador");
    fireEvent.change(select, { target: { value: "colab-1" } });

    await waitFor(() => {
      expect(listAnalysesSpy).toHaveBeenLastCalledWith(expect.objectContaining({ owner_id: "colab-1" }));
    });
  });

  it("filters the list by a date range", async () => {
    const listAnalysesSpy = vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    fireEvent.change(screen.getByLabelText("Data inicial"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("Data final"), { target: { value: "2026-01-31" } });

    await waitFor(() => {
      expect(listAnalysesSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({ date_from: "2026-01-01", date_to: "2026-01-31" }),
      );
    });
  });

  it("sends the participant search to the server instead of filtering locally", async () => {
    const listAnalysesSpy = vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    fireEvent.change(screen.getByLabelText("Buscar participante"), { target: { value: "jo" } });

    await waitFor(() => {
      expect(listAnalysesSpy).toHaveBeenLastCalledWith(expect.objectContaining({ participant_name: "jo" }));
    });
  });

  it("recalculates the KPI cards from the status pill, not from the global stats", async () => {
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue({
      ...ANALYSES,
      items: [
        ANALYSES.items[0],
        {
          ...ANALYSES.items[0],
          id: "2",
          participant_name: "Maria Souza",
          status: "FAILED",
          overall_score: null,
          overall_farol_level: null,
        },
      ],
      total: 2,
    });
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    const kpiBefore = screen.getByText("Minhas análises").closest(".kpi-card");
    expect(kpiBefore).toHaveTextContent("2");

    fireEvent.click(screen.getByRole("button", { name: /Com falha/ }));

    await screen.findByText("Maria Souza");
    expect(screen.queryByText("João Silva")).not.toBeInTheDocument();
    const kpiAfter = screen.getByText("Minhas análises").closest(".kpi-card");
    expect(kpiAfter).toHaveTextContent("1");
    const notaCard = screen.getByText("Minha nota média").closest(".kpi-card");
    expect(notaCard).toHaveTextContent("—");
  });

  it("only shows Limpar filtros when a filter is active, and resets everything on click", async () => {
    const listAnalysesSpy = vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    await screen.findByText("João Silva");
    expect(screen.queryByRole("button", { name: "Limpar filtros" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Buscar participante"), { target: { value: "jo" } });
    fireEvent.click(screen.getByRole("button", { name: /Com falha/ }));

    const clearButton = await screen.findByRole("button", { name: "Limpar filtros" });
    fireEvent.click(clearButton);

    expect(screen.getByLabelText("Buscar participante")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Limpar filtros" })).not.toBeInTheDocument();
    await waitFor(() => {
      expect(listAnalysesSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({ participant_name: undefined }),
      );
    });
  });
});
