export interface ChatMessageResponse {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessageResponse[];
}
