import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CalibrationPage from "./CalibrationPage";
import * as methodologyApi from "../api/methodology";
import type { MethodologyDetail, MethodologySummary } from "../types/methodology";

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CalibrationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const PUBLISHED_SUMMARY: MethodologySummary = {
  id: "v1",
  calibration_version: "93x7 Franq | Calibration v1.0",
  methodology_name: "93x7®",
  status: "PUBLISHED",
  created_at: "2026-01-01T00:00:00Z",
  published_at: "2026-01-02T00:00:00Z",
  archived_at: null,
};

const DRAFT_SUMMARY: MethodologySummary = {
  ...PUBLISHED_SUMMARY,
  id: "v2",
  calibration_version: "v2 (rascunho)",
  status: "DRAFT",
  published_at: null,
};

function detailFor(summary: MethodologySummary): MethodologyDetail {
  return {
    ...summary,
    project: "Projeto Franq",
    content: {},
    categories: [
      { key: "posicionamento", label: "Posicionamento", description: "desc", order_index: 0, extra: {} },
    ],
    calibrators: [
      { key: "excelente", label: "Excelente desempenho", color: "verde", min: 8, max: 10, order_index: 0 },
    ],
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("CalibrationPage", () => {
  it("lists versions and shows the detail of the first one by default", async () => {
    vi.spyOn(methodologyApi, "listMethodologies").mockResolvedValue([PUBLISHED_SUMMARY]);
    vi.spyOn(methodologyApi, "getMethodology").mockResolvedValue(detailFor(PUBLISHED_SUMMARY));

    renderPage();

    expect(await screen.findByText("Posicionamento")).toBeInTheDocument();
    expect(screen.getAllByText("Ativa").length).toBeGreaterThan(0);
  });

  it("shows editable controls only for a DRAFT version", async () => {
    vi.spyOn(methodologyApi, "listMethodologies").mockResolvedValue([DRAFT_SUMMARY]);
    vi.spyOn(methodologyApi, "getMethodology").mockResolvedValue(detailFor(DRAFT_SUMMARY));

    renderPage();

    // Rascunho renderiza o label do critério como <input>, não texto — por isso
    // findByDisplayValue, não findByText (ver teste seguinte para o caso read-only).
    expect(await screen.findByDisplayValue("Posicionamento")).toBeInTheDocument();
    expect(screen.getByText("Salvar rascunho")).toBeInTheDocument();
    expect(screen.getByText(/^Publicar/)).toBeInTheDocument();
  });

  it("does not show editable controls for a PUBLISHED version", async () => {
    vi.spyOn(methodologyApi, "listMethodologies").mockResolvedValue([PUBLISHED_SUMMARY]);
    vi.spyOn(methodologyApi, "getMethodology").mockResolvedValue(detailFor(PUBLISHED_SUMMARY));

    renderPage();

    await screen.findByText("Posicionamento");
    expect(screen.queryByText("Salvar rascunho")).not.toBeInTheDocument();
  });

  it("publishes the selected draft after confirmation", async () => {
    vi.spyOn(methodologyApi, "listMethodologies").mockResolvedValue([DRAFT_SUMMARY]);
    vi.spyOn(methodologyApi, "getMethodology").mockResolvedValue(detailFor(DRAFT_SUMMARY));
    const publishSpy = vi
      .spyOn(methodologyApi, "publishMethodology")
      .mockResolvedValue({ ...detailFor(DRAFT_SUMMARY), status: "PUBLISHED" });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPage();

    await screen.findByDisplayValue("Posicionamento");
    const publishButton = screen.getByText(/^Publicar/);
    fireEvent.click(publishButton);

    await waitFor(() => expect(publishSpy).toHaveBeenCalledWith("v2"));
  });
});
