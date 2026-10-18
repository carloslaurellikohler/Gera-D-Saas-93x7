import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import * as runtimeSettingsApi from "../api/runtimeSettings";
import { ConfirmProvider } from "../context/ConfirmContext";
import type { RuntimeSettings } from "../types/runtimeSettings";
import SettingsPage from "./SettingsPage";

const SETTINGS: RuntimeSettings = {
  daily_analysis_limit_per_owner: 4,
  assistant_daily_message_limit: 30,
  analysis_model: "gpt-6-luna",
  analysis_temperature: 0.2,
  assistant_model: "gpt-4.1",
  assistant_temperature: 0.3,
  reasoning_model_prefixes: ["o1", "o3", "o4", "gpt-5", "gpt-6"],
  analysis_model_priced: true,
  assistant_model_priced: true,
  updated_at: "2026-10-17T13:45:00Z",
  updated_by_name: "Ana Admin",
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfirmProvider>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </ConfirmProvider>
    </QueryClientProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(runtimeSettingsApi, "getRuntimeSettings").mockResolvedValue(SETTINGS);
    vi.spyOn(runtimeSettingsApi, "updateRuntimeSettings").mockResolvedValue(SETTINGS);
  });

  it("mostra os valores vindos do servidor", async () => {
    renderPage();

    expect(await screen.findByLabelText("Análises por dia, por colaborador")).toHaveValue(4);
    expect(screen.getByLabelText("Perguntas por dia ao assistente")).toHaveValue(30);
    expect(screen.getByLabelText("Modelo", { selector: "#analysis-model" })).toHaveValue(
      "gpt-6-luna",
    );
    expect(screen.getByLabelText("Modelo", { selector: "#assistant-model" })).toHaveValue(
      "gpt-4.1",
    );
  });

  it("mostra quem alterou e quando", async () => {
    renderPage();

    expect(await screen.findByText(/Alterado por Ana Admin em/)).toBeInTheDocument();
  });

  it("diz que nunca foi alterado quando não há registro de edição", async () => {
    vi.spyOn(runtimeSettingsApi, "getRuntimeSettings").mockResolvedValue({
      ...SETTINGS,
      updated_at: null,
      updated_by_name: null,
    });
    renderPage();

    expect(await screen.findByText(/Nunca alterado pela tela/)).toBeInTheDocument();
  });

  it("desabilita a temperatura quando o modelo digitado é de raciocínio", async () => {
    renderPage();
    await screen.findByLabelText("Análises por dia, por colaborador");

    // O modelo da análise já é gpt-6-luna (prefixo gpt-6), o do assistente é gpt-4.1.
    expect(screen.getByLabelText("Temperatura", { selector: "#analysis-temperature" })).toBeDisabled();
    expect(
      screen.getByLabelText("Temperatura", { selector: "#assistant-temperature" }),
    ).toBeEnabled();
    expect(screen.getByText(/Modelos de raciocínio ignoram temperatura/)).toBeInTheDocument();
  });

  it("testa o modelo com o valor digitado, não com o salvo", async () => {
    const testSpy = vi
      .spyOn(runtimeSettingsApi, "testAiModel")
      .mockResolvedValue({ ok: true, message: "O modelo respondeu normalmente." });
    renderPage();

    const input = await screen.findByLabelText("Modelo", { selector: "#analysis-model" });
    await userEvent.clear(input);
    await userEvent.type(input, "gpt-4.1-mini");
    await userEvent.click(screen.getByRole("button", { name: "Testar modelo da análise" }));

    await waitFor(() =>
      expect(testSpy).toHaveBeenCalledWith({ model_name: "gpt-4.1-mini", temperature: 0.2 }),
    );
    expect(await screen.findByText("O modelo respondeu normalmente.")).toBeInTheDocument();
  });

  it("mostra a mensagem de erro quando o modelo não existe", async () => {
    vi.spyOn(runtimeSettingsApi, "testAiModel").mockRejectedValue(
      new ApiError(400, "O modelo não respondeu: The model `xpto` does not exist"),
    );
    renderPage();

    await screen.findByLabelText("Análises por dia, por colaborador");
    await userEvent.click(screen.getByRole("button", { name: "Testar modelo do assistente" }));

    expect(await screen.findByText(/does not exist/)).toBeInTheDocument();
  });

  it("salva enviando números, não strings", async () => {
    const updateSpy = vi
      .spyOn(runtimeSettingsApi, "updateRuntimeSettings")
      .mockResolvedValue(SETTINGS);
    renderPage();

    const limit = await screen.findByLabelText("Análises por dia, por colaborador");
    await userEvent.clear(limit);
    await userEvent.type(limit, "9");
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() =>
      expect(updateSpy).toHaveBeenCalledWith({
        daily_analysis_limit_per_owner: 9,
        assistant_daily_message_limit: 30,
        analysis_model: "gpt-6-luna",
        analysis_temperature: 0.2,
        assistant_model: "gpt-4.1",
        assistant_temperature: 0.3,
      }),
    );
    expect(await screen.findByText(/Configuração salva/)).toBeInTheDocument();
  });

  it("pede confirmação antes de salvar um modelo alterado sem teste", async () => {
    const updateSpy = vi
      .spyOn(runtimeSettingsApi, "updateRuntimeSettings")
      .mockResolvedValue(SETTINGS);
    renderPage();

    const input = await screen.findByLabelText("Modelo", { selector: "#analysis-model" });
    await userEvent.clear(input);
    await userEvent.type(input, "modelo-novo");
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/sem passar pelo teste/)).toBeInTheDocument();
    expect(updateSpy).not.toHaveBeenCalled();

    await userEvent.click(within(dialog).getByRole("button", { name: "Salvar assim" }));
    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
  });

  it("salva sem confirmação quando o modelo alterado passou no teste", async () => {
    vi.spyOn(runtimeSettingsApi, "testAiModel").mockResolvedValue({
      ok: true,
      message: "O modelo respondeu normalmente.",
    });
    const updateSpy = vi
      .spyOn(runtimeSettingsApi, "updateRuntimeSettings")
      .mockResolvedValue(SETTINGS);
    renderPage();

    const input = await screen.findByLabelText("Modelo", { selector: "#analysis-model" });
    await userEvent.clear(input);
    await userEvent.type(input, "modelo-novo");
    await userEvent.click(screen.getByRole("button", { name: "Testar modelo da análise" }));
    await screen.findByText("O modelo respondeu normalmente.");

    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("avisa com link para custos quando o modelo não tem preço cadastrado", async () => {
    vi.spyOn(runtimeSettingsApi, "getRuntimeSettings").mockResolvedValue({
      ...SETTINGS,
      analysis_model_priced: false,
    });
    renderPage();

    expect(await screen.findByText(/não tem preço cadastrado/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Custos de IA" })).toHaveAttribute(
      "href",
      "/custos-ia",
    );
  });

  it("mostra erro quando a configuração não carrega", async () => {
    vi.spyOn(runtimeSettingsApi, "getRuntimeSettings").mockRejectedValue(new Error("falhou"));
    renderPage();

    expect(
      await screen.findByText("Não foi possível carregar as configurações."),
    ).toBeInTheDocument();
  });
});
