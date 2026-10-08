import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { useChatHistory } from "../hooks/useChatHistory";
import { useSendChatMessage } from "../hooks/useSendChatMessage";
import { useStartNewConversation } from "../hooks/useStartNewConversation";

const SUGGESTIONS = [
  "Sugira 3 perguntas de sondagem",
  "Como evoluí desde o mês passado?",
  "O que é o Pilar 7?",
];

export default function AssistantPage() {
  const history = useChatHistory();
  const sendMessage = useSendChatMessage();
  const startNewConversation = useStartNewConversation();
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [rateLimited, setRateLimited] = useState(false);
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [history.data?.messages.length, sendMessage.isPending, pendingUserMessage]);

  async function handleSend(content: string) {
    const trimmed = content.trim();
    if (!trimmed || sendMessage.isPending) return;
    setError(null);
    setInput("");
    setPendingUserMessage(trimmed);
    try {
      await sendMessage.mutateAsync(trimmed);
      setPendingUserMessage(null);
    } catch (err) {
      setPendingUserMessage(null);
      if (err instanceof ApiError && err.status === 429) {
        setRateLimited(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Erro ao enviar mensagem.");
      }
    }
  }

  async function handleStartNewConversation() {
    setInput("");
    setError(null);
    setRateLimited(false);
    await startNewConversation.mutateAsync();
  }

  const messages = history.data?.messages ?? [];

  return (
    // height fixa (não flex/minHeight) para o overflow:auto da área de mensagens, abaixo,
    // conseguir rolar internamente em vez de a página toda crescer; 64px = padding
    // vertical (32px topo + 32px base) de .app-main em App.css.
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 280px",
        gap: 20,
        height: "calc(100svh - 64px)",
      }}
    >
      <div className="card" style={{ padding: 0, display: "flex", flexDirection: "column", minHeight: 0 }}>
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--border-secondary)",
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <span
            style={{
              width: 36,
              height: 36,
              borderRadius: "100px",
              background: "var(--gerad-navy)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name="auto_awesome" size={20} filled color="var(--gerad-gold)" />
          </span>
          <span style={{ display: "flex", flexDirection: "column" }}>
            <b style={{ fontFamily: "var(--font-brand)", fontSize: 17, color: "var(--gerad-navy)" }}>
              Assistente GerAD
            </b>
            <span className="page-subtitle" style={{ fontSize: 12 }}>
              Dúvidas sobre a metodologia 93x7® e seus resultados
            </span>
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginLeft: "auto", fontSize: 13, height: 36, padding: "0 14px" }}
            disabled={sendMessage.isPending || startNewConversation.isPending || messages.length === 0}
            onClick={handleStartNewConversation}
          >
            <Icon name="add_comment" size={16} style={{ marginRight: 6 }} />
            Nova Conversa
          </button>
        </div>

        <div style={{ flex: 1, padding: 24, display: "flex", flexDirection: "column", gap: 18, overflow: "auto" }}>
          {history.isLoading && <p className="page-subtitle">Carregando...</p>}
          {history.isError && <p className="error-text">Não foi possível carregar o histórico.</p>}

          {!history.isLoading && !history.isError && messages.length === 0 && (
            <EmptyState
              icon="forum"
              title="Comece uma conversa"
              description="Pergunte sobre a metodologia 93x7® ou sobre suas análises concluídas."
            >
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingTop: 6, justifyContent: "center" }}>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: 13, height: "auto", padding: "8px 14px", borderRadius: "100px" }}
                    onClick={() => handleSend(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </EmptyState>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              style={
                message.role === "user"
                  ? {
                      alignSelf: "flex-end",
                      maxWidth: "70%",
                      background: "var(--gerad-navy)",
                      color: "#fff",
                      borderRadius: "16px 16px 4px 16px",
                      padding: "12px 16px",
                      fontSize: 14,
                      lineHeight: 1.55,
                      whiteSpace: "pre-wrap",
                    }
                  : {
                      alignSelf: "flex-start",
                      maxWidth: "80%",
                      background: "var(--gray-50)",
                      border: "1px solid var(--border-secondary)",
                      borderRadius: "16px 16px 16px 4px",
                      padding: "14px 18px",
                      fontSize: 14,
                      lineHeight: 1.65,
                      whiteSpace: "pre-wrap",
                    }
              }
            >
              {message.content}
            </div>
          ))}

          {pendingUserMessage && (
            <div
              style={{
                alignSelf: "flex-end",
                maxWidth: "70%",
                background: "var(--gerad-navy)",
                color: "#fff",
                borderRadius: "16px 16px 4px 16px",
                padding: "12px 16px",
                fontSize: 14,
                lineHeight: 1.55,
                whiteSpace: "pre-wrap",
              }}
            >
              {pendingUserMessage}
            </div>
          )}

          {sendMessage.isPending && (
            <div
              style={{
                alignSelf: "flex-start",
                maxWidth: "80%",
                background: "var(--gray-50)",
                border: "1px solid var(--border-secondary)",
                borderRadius: "16px 16px 16px 4px",
                padding: "14px 18px",
                fontSize: 14,
                color: "var(--content-tertiary)",
              }}
            >
              Pensando
              <span className="ui-thinking-dot">.</span>
              <span className="ui-thinking-dot">.</span>
              <span className="ui-thinking-dot">.</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div style={{ padding: "0 24px" }}>
            <ErrorBanner>{error}</ErrorBanner>
          </div>
        )}

        {rateLimited ? (
          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid var(--border-secondary)",
              fontSize: 14,
              color: "var(--content-tertiary)",
            }}
          >
            Você atingiu o limite de perguntas de hoje. Volte amanhã.
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(input);
            }}
            style={{
              padding: "16px 24px",
              borderTop: "1px solid var(--border-secondary)",
              display: "flex",
              gap: 12,
              alignItems: "center",
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sendMessage.isPending}
              placeholder="Pergunte sobre a metodologia ou sobre suas análises"
              style={{
                flex: 1,
                height: 48,
                border: "1px solid var(--border-primary)",
                borderRadius: 14,
                padding: "0 16px",
                fontSize: 14,
              }}
            />
            <button
              type="submit"
              aria-label="Enviar"
              disabled={sendMessage.isPending || !input.trim()}
              style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                background: "var(--gerad-gold)",
                color: "var(--gerad-navy)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "none",
                cursor: sendMessage.isPending || !input.trim() ? "default" : "pointer",
                opacity: sendMessage.isPending || !input.trim() ? 0.6 : 1,
              }}
            >
              <Icon name="send" size={22} />
            </button>
          </form>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card">
          <span className="kpi-label">Contexto</span>
          <p style={{ fontSize: 13, lineHeight: 1.7, marginTop: 8 }}>
            O assistente responde somente com base em análises já concluídas e deve apoiar, não
            substituir, a avaliação do gestor.
          </p>
        </div>
      </div>
    </div>
  );
}
