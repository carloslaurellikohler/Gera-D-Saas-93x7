import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LearningPathDetailPage from "./LearningPathDetailPage";
import * as learningPathsApi from "../api/learningPaths";
import type { LearningPathDetail, EnrolledLearningPathSummary } from "../types/learningPath";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ id: "path-1" }),
  };
});

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LearningPathDetailPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const DETAIL: LearningPathDetail = {
  id: "path-1",
  title: "Trilha de Sondagem",
  description: null,
  criterion_key: "sondagem",
  estimated_duration_minutes: null,
  created_at: "2026-01-01T00:00:00Z",
  items: [
    {
      id: "item-1",
      order_index: 0,
      completed: false,
      content: {
        id: "content-1",
        title: "Material 1",
        description: null,
        criterion_key: null,
        kind: "LINK",
        file_path: null,
        external_url: "https://example.com",
        uploaded_by_id: null,
        created_at: "2026-01-01T00:00:00Z",
      },
    },
  ],
};

function enrolledSummary(overrides: Partial<EnrolledLearningPathSummary> = {}): EnrolledLearningPathSummary {
  return {
    id: "path-1",
    title: "Trilha de Sondagem",
    description: null,
    criterion_key: "sondagem",
    estimated_duration_minutes: null,
    item_count: 1,
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

describe("LearningPathDetailPage", () => {
  it("shows the enroll button when the user is not enrolled", async () => {
    vi.spyOn(learningPathsApi, "getLearningPath").mockResolvedValue(DETAIL);
    vi.spyOn(learningPathsApi, "listEnrolledLearningPaths").mockResolvedValue([]);

    renderPage();

    expect(await screen.findByRole("button", { name: "Inscrever-se" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Marcar como concluído" })).not.toBeInTheDocument();
  });

  it("shows completion buttons instead of enroll when already enrolled", async () => {
    vi.spyOn(learningPathsApi, "getLearningPath").mockResolvedValue(DETAIL);
    vi.spyOn(learningPathsApi, "listEnrolledLearningPaths").mockResolvedValue([enrolledSummary()]);

    renderPage();

    expect(await screen.findByRole("button", { name: "Marcar como concluído" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Inscrever-se" })).not.toBeInTheDocument();
  });

  it("calls completeLearningPathItem with the correct ids when marking a material as complete", async () => {
    const user = userEvent.setup();
    vi.spyOn(learningPathsApi, "getLearningPath").mockResolvedValue(DETAIL);
    vi.spyOn(learningPathsApi, "listEnrolledLearningPaths").mockResolvedValue([enrolledSummary()]);
    const completeSpy = vi.spyOn(learningPathsApi, "completeLearningPathItem").mockResolvedValue(undefined);

    renderPage();

    await user.click(await screen.findByRole("button", { name: "Marcar como concluído" }));

    expect(completeSpy).toHaveBeenCalledWith("path-1", "item-1");
  });
});
