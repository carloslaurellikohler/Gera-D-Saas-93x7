import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import NewAnalysisPage from "./NewAnalysisPage";
import * as analysesApi from "../api/analyses";
import * as authApi from "../api/auth";
import * as usersApi from "../api/users";
import { AuthProvider } from "../context/AuthContext";
import type { User } from "../types/auth";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

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

const GESTOR: User = {
  ...COLABORADOR,
  id: "gestor-1",
  name: "Gestora Teste",
  email: "gestora@example.com",
  role: "GESTOR",
};

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <NewAnalysisPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function makeTextFile(name = "transcricao.txt") {
  return new File(["CS: Oi\nPB: Oi"], name, { type: "text/plain" });
}

beforeEach(() => {
  mockNavigate.mockReset();
  vi.restoreAllMocks();
  vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(COLABORADOR);
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

  it("does not show the assignee selector for a COLABORADOR", async () => {
    renderPage();

    await waitFor(() => expect(screen.queryByLabelText("Atribuir a")).not.toBeInTheDocument());
  });

  it("shows the assignee selector and requires it for a GESTOR", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(GESTOR);
    vi.spyOn(usersApi, "listMyTeam").mockResolvedValue([
      { ...COLABORADOR, id: "colab-1", name: "Colaboradora Teste" },
    ]);
    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText("Atribuir a");

    await user.type(screen.getByLabelText("Participante"), "João Silva");
    await user.selectOptions(screen.getByLabelText("Objetivo"), "Onboarding");
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeTextFile());
    await user.click(screen.getByRole("button", { name: "Iniciar análise" }));

    expect(await screen.findByText("Atribua a análise a um colaborador da sua equipe.")).toBeInTheDocument();
  });

  it("includes owner_id in the payload when a GESTOR assigns the analysis", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(GESTOR);
    vi.spyOn(usersApi, "listMyTeam").mockResolvedValue([
      { ...COLABORADOR, id: "colab-1", name: "Colaboradora Teste" },
    ]);
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
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("option", { name: "Colaboradora Teste" });
    await user.selectOptions(screen.getByLabelText("Atribuir a"), "colab-1");
    await user.type(screen.getByLabelText("Participante"), "João Silva");
    await user.selectOptions(screen.getByLabelText("Objetivo"), "Onboarding");
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeTextFile());
    await user.click(screen.getByRole("button", { name: "Iniciar análise" }));

    await waitFor(() => expect(createSpy).toHaveBeenCalledOnce());
    expect(createSpy.mock.calls[0]?.[0]).toMatchObject({ owner_id: "colab-1" });
  });

  it("shows the quota card with used/limit for a COLABORADOR", async () => {
    vi.spyOn(analysesApi, "getAnalysisQuota").mockResolvedValue({
      owner_id: "colab-1",
      used: 2,
      limit: 4,
      remaining: 2,
      exempt: false,
    });
    renderPage();

    expect(await screen.findByText("2 de 4 usadas hoje")).toBeInTheDocument();
  });

  it("disables submit and shows a warning when the quota is exhausted", async () => {
    vi.spyOn(analysesApi, "getAnalysisQuota").mockResolvedValue({
      owner_id: "colab-1",
      used: 4,
      limit: 4,
      remaining: 0,
      exempt: false,
    });
    renderPage();

    await screen.findByText("4 de 4 usadas hoje");
    expect(screen.getByText("Limite diário atingido para este colaborador.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Iniciar análise/ })).toBeDisabled();
  });

  it("shows an exempt message instead of the progress bar for an exempt user", async () => {
    vi.spyOn(analysesApi, "getAnalysisQuota").mockResolvedValue({
      owner_id: "admin-1",
      used: 10,
      limit: 4,
      remaining: 4,
      exempt: true,
    });
    renderPage();

    expect(await screen.findByText("Sem limite diário (administrador).")).toBeInTheDocument();
  });

  it("does not query the quota for a GESTOR before a colaborador is selected", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(GESTOR);
    vi.spyOn(usersApi, "listMyTeam").mockResolvedValue([
      { ...COLABORADOR, id: "colab-1", name: "Colaboradora Teste" },
    ]);
    const quotaSpy = vi.spyOn(analysesApi, "getAnalysisQuota").mockResolvedValue({
      owner_id: "colab-1",
      used: 1,
      limit: 4,
      remaining: 3,
      exempt: false,
    });
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("option", { name: "Colaboradora Teste" });
    expect(screen.queryByText("Cota diária de análises")).not.toBeInTheDocument();
    expect(quotaSpy).not.toHaveBeenCalled();

    await user.selectOptions(screen.getByLabelText("Atribuir a"), "colab-1");

    await screen.findByText("1 de 4 usadas hoje");
    expect(quotaSpy).toHaveBeenCalledWith("colab-1");
  });
});
