import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LibraryPage from "./LibraryPage";
import { AuthProvider } from "../context/AuthContext";
import * as authApi from "../api/auth";
import * as learningPathsApi from "../api/learningPaths";
import * as contentApi from "../api/content";
import type { LearningPathSummary } from "../types/learningPath";
import type { User } from "../types/auth";

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <LibraryPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const USER: User = {
  id: "user-1",
  name: "Usuária Teste",
  email: "user@example.com",
  role: "USER",
  status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

const PATH: LearningPathSummary = {
  id: "path-1",
  title: "Trilha de Sondagem",
  description: null,
  criterion_key: "sondagem",
  estimated_duration_minutes: null,
  item_count: 2,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(USER);
  vi.spyOn(learningPathsApi, "getRecommendedLearningPaths").mockResolvedValue([]);
  vi.spyOn(contentApi, "listContent").mockResolvedValue([]);
});

describe("LibraryPage", () => {
  it("renders trail cards as links to the trail detail page", async () => {
    vi.spyOn(learningPathsApi, "listLearningPaths").mockResolvedValue([PATH]);

    renderPage();

    const link = await screen.findByRole("link", { name: /Trilha de Sondagem/ });
    expect(link).toHaveAttribute("href", "/biblioteca/trilhas/path-1");
  });
});
