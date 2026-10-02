import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import InProgressTab from "./InProgressTab";
import * as learningPathsApi from "../../api/learningPaths";
import type { EnrolledLearningPathSummary } from "../../types/learningPath";

function renderComponent() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <InProgressTab />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function makeEnrolledPath(overrides: Partial<EnrolledLearningPathSummary> = {}): EnrolledLearningPathSummary {
  return {
    id: "path-1",
    title: "Trilha de Sondagem",
    description: null,
    criterion_key: "sondagem",
    estimated_duration_minutes: null,
    item_count: 2,
    completed_count: 0,
    progress_percent: 0,
    is_completed: false,
    enrolled_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("InProgressTab", () => {
  it("shows an empty state when the user has no enrollments", async () => {
    vi.spyOn(learningPathsApi, "listEnrolledLearningPaths").mockResolvedValue([]);

    renderComponent();

    expect(
      await screen.findByText("Você ainda não se inscreveu em nenhuma trilha"),
    ).toBeInTheDocument();
  });

  it("lists an incomplete path under 'Em andamento'", async () => {
    vi.spyOn(learningPathsApi, "listEnrolledLearningPaths").mockResolvedValue([
      makeEnrolledPath({ is_completed: false }),
    ]);

    renderComponent();

    expect(await screen.findByRole("heading", { name: "Em andamento" })).toBeInTheDocument();
    expect(screen.getByText("Trilha de Sondagem")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Concluídas" })).not.toBeInTheDocument();
  });

  it("lists a fully completed path under 'Concluídas'", async () => {
    vi.spyOn(learningPathsApi, "listEnrolledLearningPaths").mockResolvedValue([
      makeEnrolledPath({ is_completed: true, completed_count: 2, progress_percent: 100 }),
    ]);

    renderComponent();

    expect(await screen.findByRole("heading", { name: "Concluídas" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Em andamento" })).not.toBeInTheDocument();
  });
});
