import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LibraryPage from "./LibraryPage";
import { AuthProvider } from "../context/AuthContext";
import * as authApi from "../api/auth";
import * as learningPathsApi from "../api/learningPaths";
import * as contentApi from "../api/content";
import { ApiError } from "../api/client";
import type { LearningPathDetail, LearningPathSummary } from "../types/learningPath";
import type { ContentResponse } from "../types/content";
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

const ADMIN: User = { ...USER, id: "admin-1", name: "Admin Teste", role: "ADMIN" };

const PATH: LearningPathSummary = {
  id: "path-1",
  title: "Trilha de Sondagem",
  description: null,
  criterion_key: "sondagem",
  estimated_duration_minutes: null,
  item_count: 2,
  created_at: "2026-01-01T00:00:00Z",
};

const PATH_DETAIL: LearningPathDetail = {
  id: "path-1",
  title: "Trilha de Sondagem",
  description: null,
  criterion_key: "sondagem",
  estimated_duration_minutes: null,
  created_at: "2026-01-01T00:00:00Z",
  items: [],
};

const MATERIAL: ContentResponse = {
  id: "content-1",
  title: "Vídeo-aula",
  description: null,
  criterion_key: null,
  kind: "LINK",
  file_path: null,
  external_url: "https://example.com/video",
  uploaded_by_id: null,
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

  it("does not show edit/delete buttons on trail cards for a regular user", async () => {
    vi.spyOn(learningPathsApi, "listLearningPaths").mockResolvedValue([PATH]);

    renderPage();

    await screen.findByRole("link", { name: /Trilha de Sondagem/ });
    expect(screen.queryByRole("button", { name: "Editar trilha" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Excluir trilha" })).not.toBeInTheDocument();
  });

  it("shows edit/delete buttons on trail cards for an admin", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(learningPathsApi, "listLearningPaths").mockResolvedValue([PATH]);

    renderPage();

    expect(await screen.findByRole("button", { name: "Editar trilha" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Excluir trilha" })).toBeInTheDocument();
  });

  it("deletes a trail after confirmation", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(learningPathsApi, "listLearningPaths").mockResolvedValue([PATH]);
    const deleteSpy = vi.spyOn(learningPathsApi, "deleteLearningPath").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPage();

    await user.click(await screen.findByRole("button", { name: "Excluir trilha" }));

    expect(deleteSpy.mock.calls[0]?.[0]).toBe("path-1");
  });

  it("does not delete a trail when confirmation is cancelled", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(learningPathsApi, "listLearningPaths").mockResolvedValue([PATH]);
    const deleteSpy = vi.spyOn(learningPathsApi, "deleteLearningPath").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    renderPage();

    await user.click(await screen.findByRole("button", { name: "Excluir trilha" }));

    expect(deleteSpy).not.toHaveBeenCalled();
  });

  it("opens the trail edit form pre-filled and submits the update payload", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(learningPathsApi, "listLearningPaths").mockResolvedValue([PATH]);
    vi.spyOn(learningPathsApi, "getLearningPath").mockResolvedValue(PATH_DETAIL);
    const updateSpy = vi
      .spyOn(learningPathsApi, "updateLearningPath")
      .mockResolvedValue(PATH_DETAIL);

    renderPage();

    await user.click(await screen.findByRole("button", { name: "Editar trilha" }));

    const titleInput = await screen.findByLabelText("Título da trilha");
    expect(titleInput).toHaveValue("Trilha de Sondagem");

    await user.clear(titleInput);
    await user.type(titleInput, "Trilha atualizada");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(updateSpy).toHaveBeenCalledWith(
      "path-1",
      expect.objectContaining({ title: "Trilha atualizada" }),
    );
  });

  it("does not show edit/delete buttons on material cards for a regular user", async () => {
    const user = userEvent.setup();
    vi.spyOn(contentApi, "listContent").mockResolvedValue([MATERIAL]);

    renderPage();
    await user.click(screen.getByRole("button", { name: "Materiais de apoio" }));

    await screen.findByText("Vídeo-aula");
    expect(screen.queryByRole("button", { name: "Editar material" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Excluir material" })).not.toBeInTheDocument();
  });

  it("shows edit/delete buttons on material cards for an admin", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(contentApi, "listContent").mockResolvedValue([MATERIAL]);

    renderPage();
    await user.click(screen.getByRole("button", { name: "Materiais de apoio" }));

    expect(await screen.findByRole("button", { name: "Editar material" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Excluir material" })).toBeInTheDocument();
  });

  it("deletes a material after confirmation", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(contentApi, "listContent").mockResolvedValue([MATERIAL]);
    const deleteSpy = vi.spyOn(contentApi, "deleteContent").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPage();
    await user.click(screen.getByRole("button", { name: "Materiais de apoio" }));
    await user.click(await screen.findByRole("button", { name: "Excluir material" }));

    expect(deleteSpy.mock.calls[0]?.[0]).toBe("content-1");
  });

  it("shows a friendly error when deleting a material still referenced by a trail", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(contentApi, "listContent").mockResolvedValue([MATERIAL]);
    vi
      .spyOn(contentApi, "deleteContent")
      .mockRejectedValue(new ApiError(409, "Este material ainda está vinculado a uma ou mais trilhas."));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPage();
    await user.click(screen.getByRole("button", { name: "Materiais de apoio" }));
    await user.click(await screen.findByRole("button", { name: "Excluir material" }));

    expect(
      await screen.findByText("Este material ainda está vinculado a uma ou mais trilhas."),
    ).toBeInTheDocument();
  });

  it("opens the material edit form pre-filled and submits the update payload", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
    vi.spyOn(contentApi, "listContent").mockResolvedValue([MATERIAL]);
    const updateSpy = vi.spyOn(contentApi, "updateContent").mockResolvedValue(MATERIAL);

    renderPage();
    await user.click(screen.getByRole("button", { name: "Materiais de apoio" }));
    await user.click(await screen.findByRole("button", { name: "Editar material" }));

    const titleInput = await screen.findByLabelText("Título");
    expect(titleInput).toHaveValue("Vídeo-aula");

    await user.clear(titleInput);
    await user.type(titleInput, "Vídeo-aula atualizada");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(updateSpy).toHaveBeenCalledWith(
      "content-1",
      expect.objectContaining({ title: "Vídeo-aula atualizada" }),
    );
  });
});
