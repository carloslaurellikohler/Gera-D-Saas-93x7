import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminDashboardPage from "./AdminDashboardPage";
import * as dashboardApi from "../api/dashboard";
import type { DashboardStatsResponse } from "../types/dashboard";

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const STATS: DashboardStatsResponse = {
  period: "6m",
  volume_by_status: [
    { status: "COMPLETED", count: 5 },
    { status: "UPLOADED", count: 2 },
  ],
  farol_distribution: [{ label: "Excelente desempenho", level: "excelente", count: 5, pct: "100%" }],
  trend: [{ period_start: "2026-01-05", count: 5, avg_score: 8.4 }],
  board: [
    { pb_id: "ana", name: "Ana Silva", count: 3, avg_score: 8.4, level: "excelente", trend: "up" },
  ],
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("AdminDashboardPage", () => {
  it("renders aggregated KPIs and board from the API", async () => {
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue(STATS);

    renderPage();

    expect(await screen.findByText("7")).toBeInTheDocument(); // total volume
    expect(screen.getByText("Ana Silva")).toBeInTheDocument();
    expect(screen.getAllByText("Excelente").length).toBeGreaterThan(0);
  });

  it("shows an empty state for the board when there are no completed analyses", async () => {
    vi.spyOn(dashboardApi, "getDashboardStats").mockResolvedValue({
      ...STATS,
      farol_distribution: [],
      trend: [],
      board: [],
    });

    renderPage();

    expect(await screen.findByText("Nenhuma análise concluída no período.")).toBeInTheDocument();
  });
});
