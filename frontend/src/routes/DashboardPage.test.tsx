import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DashboardPage from "./DashboardPage";
import * as analysesApi from "../api/analyses";
import * as authApi from "../api/auth";
import * as dashboardApi from "../api/dashboard";
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
    { id: "1", participant_name: "João Silva", objective: "Onboarding", status: "COMPLETED", created_at: "2026-01-01T00:00:00Z" },
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
  board: null,
  team_board: null,
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(COLABORADOR);
});

describe("DashboardPage", () => {
  it("renders the personal KPI block scoped to the current user's own analyses", async () => {
    vi.spyOn(analysesApi, "listAnalyses").mockResolvedValue(ANALYSES);
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    expect(await screen.findByText("Minhas análises")).toBeInTheDocument();
    expect(screen.getByText("7.2")).toBeInTheDocument();
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
    expect(screen.getByText("Colaboradora Teste")).toBeInTheDocument();
  });
});
