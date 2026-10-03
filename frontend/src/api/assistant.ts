import { apiGet, apiPost } from "./client";
import type { ChatHistoryResponse, ChatMessageResponse } from "../types/assistant";

export function getChatHistory() {
  return apiGet<ChatHistoryResponse>("/assistant/messages");
}

export function sendChatMessage(content: string) {
  return apiPost<ChatMessageResponse>("/assistant/messages", { content });
}
