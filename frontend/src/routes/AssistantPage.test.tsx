import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AssistantPage from "./AssistantPage";
import * as assistantApi from "../api/assistant";
import { ApiError } from "../api/client";
import type { ChatMessageResponse } from "../types/assistant";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AssistantPage />
    </QueryClientProvider>,
  );
}

const USER_MESSAGE: ChatMessageResponse = {
  id: "m1",
  role: "user",
  content: "O que é o Pilar 7?",
  created_at: "2026-01-01T00:00:00Z",
};

const ASSISTANT_MESSAGE: ChatMessageResponse = {
  id: "m2",
  role: "assistant",
  content: "O Pilar 7 representa o conteúdo/resultado da conversa.",
  created_at: "2026-01-01T00:00:01Z",
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("AssistantPage", () => {
  it("shows the empty state with suggestions when there is no history", async () => {
    vi.spyOn(assistantApi, "getChatHistory").mockResolvedValue({ messages: [] });

    renderPage();

    expect(await screen.findByText("Comece uma conversa")).toBeInTheDocument();
    expect(screen.getByText("O que é o Pilar 7?")).toBeInTheDocument();
  });

  it("renders existing history messages", async () => {
    vi.spyOn(assistantApi, "getChatHistory").mockResolvedValue({
      messages: [USER_MESSAGE, ASSISTANT_MESSAGE],
    });

    renderPage();

    expect(await screen.findByText("O que é o Pilar 7?")).toBeInTheDocument();
    expect(screen.getByText("O Pilar 7 representa o conteúdo/resultado da conversa.")).toBeInTheDocument();
  });

  it("sends a message and shows the assistant reply", async () => {
    const user = userEvent.setup();
    vi.spyOn(assistantApi, "getChatHistory").mockResolvedValue({ messages: [] });
    const sendSpy = vi.spyOn(assistantApi, "sendChatMessage").mockResolvedValue(ASSISTANT_MESSAGE);

    renderPage();

    await screen.findByText("Comece uma conversa");
    const input = screen.getByPlaceholderText("Pergunte sobre a metodologia ou sobre suas análises");
    await user.type(input, "Como evoluí desde o mês passado?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));

    expect(sendSpy.mock.calls[0]?.[0]).toBe("Como evoluí desde o mês passado?");
  });

  it("shows a generic error banner when sending fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(assistantApi, "getChatHistory").mockResolvedValue({ messages: [] });
    vi.spyOn(assistantApi, "sendChatMessage").mockRejectedValue(new ApiError(500, "Erro interno."));

    renderPage();

    const input = await screen.findByPlaceholderText("Pergunte sobre a metodologia ou sobre suas análises");
    await user.type(input, "pergunta qualquer{enter}");

    expect(await screen.findByText("Erro interno.")).toBeInTheDocument();
  });

  it("starts a new conversation and shows the empty state again", async () => {
    const user = userEvent.setup();
    vi.spyOn(assistantApi, "getChatHistory")
      .mockResolvedValueOnce({ messages: [USER_MESSAGE, ASSISTANT_MESSAGE] })
      .mockResolvedValueOnce({ messages: [] });
    const startSpy = vi.spyOn(assistantApi, "startNewConversation").mockResolvedValue(undefined);

    renderPage();

    await screen.findByText("O que é o Pilar 7?");
    await user.click(screen.getByRole("button", { name: "Nova Conversa" }));

    expect(startSpy).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Comece uma conversa")).toBeInTheDocument();
    expect(
      screen.queryByText("O Pilar 7 representa o conteúdo/resultado da conversa."),
    ).not.toBeInTheDocument();
  });

  it("disables the new conversation button when there is no history yet", async () => {
    vi.spyOn(assistantApi, "getChatHistory").mockResolvedValue({ messages: [] });

    renderPage();

    expect(await screen.findByRole("button", { name: "Nova Conversa" })).toBeDisabled();
  });

  it("shows the daily limit message instead of the input on a 429", async () => {
    const user = userEvent.setup();
    vi.spyOn(assistantApi, "getChatHistory").mockResolvedValue({ messages: [] });
    vi.spyOn(assistantApi, "sendChatMessage").mockRejectedValue(
      new ApiError(429, "Você atingiu o limite de perguntas de hoje. Volte amanhã."),
    );

    renderPage();

    const input = await screen.findByPlaceholderText("Pergunte sobre a metodologia ou sobre suas análises");
    await user.type(input, "pergunta qualquer{enter}");

    expect(await screen.findByText("Você atingiu o limite de perguntas de hoje. Volte amanhã.")).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("Pergunte sobre a metodologia ou sobre suas análises"),
    ).not.toBeInTheDocument();
  });
});
