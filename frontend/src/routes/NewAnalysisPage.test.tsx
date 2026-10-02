import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import NewAnalysisPage from "./NewAnalysisPage";
import * as analysesApi from "../api/analyses";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NewAnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function makeTextFile(name = "transcricao.txt") {
  return new File(["CS: Oi\nPB: Oi"], name, { type: "text/plain" });
}

beforeEach(() => {
  mockNavigate.mockReset();
});

describe("NewAnalysisPage", () => {
  it("shows a validation error when submitting without an objective", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Participante"), "João Silva");
    await user.click(screen.getByRole("button", { name: "Iniciar análise" }));

    expect(await screen.findByText("Selecione um objetivo.")).toBeInTheDocument();
  });

  it("reveals the complement field only when objective is Outro", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.queryByLabelText("Descrição do objetivo")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Objetivo"), "Outro");
    expect(screen.getByLabelText("Descrição do objetivo")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Objetivo"), "Onboarding");
    expect(screen.queryByLabelText("Descrição do objetivo")).not.toBeInTheDocument();
  });

  it("rejects a file with an unsupported extension for the selected input type", async () => {
    renderPage();

    // "Texto" é o tipo padrão; .mp3 não é aceito para texto.
    // Usa fireEvent (não userEvent.upload) porque userEvent respeita o atributo `accept`
    // do input e filtraria o arquivo antes mesmo do onChange disparar — isso mascararia
    // o teste em vez de exercitar validate_upload-equivalente no cliente (services/validation
    // no backend; aqui, a validação de extensão em components/forms/FileDropzone.tsx).
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const badFile = new File(["fake audio"], "audio.mp3", { type: "audio/mpeg" });
    Object.defineProperty(input, "files", { value: [badFile] });
    fireEvent.change(input);

    expect(await screen.findByText(/Formato não suportado/)).toBeInTheDocument();
  });

  it("submits successfully and navigates to the processing page", async () => {
    const user = userEvent.setup();
    const createSpy = vi.spyOn(analysesApi, "createAnalysis").mockResolvedValue({
      id: "abc-123",
      participant_name: "João Silva",
      objective: "Onboarding",
      objective_complement: null,
      duration_seconds: null,
      interaction_date: null,
      input_type: "txt",
      file_name: "transcricao.txt",
      status: "UPLOADED",
      error_message: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
      started_at: null,
      completed_at: null,
    });

    renderPage();

    await user.type(screen.getByLabelText("Participante"), "João Silva");
    await user.selectOptions(screen.getByLabelText("Objetivo"), "Onboarding");

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeTextFile());

    await user.click(screen.getByRole("button", { name: "Iniciar análise" }));

    await waitFor(() => expect(createSpy).toHaveBeenCalledOnce());
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/analyses/abc-123/processing"));
  });
});
