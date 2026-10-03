import { useQuery } from "@tanstack/react-query";
import { getChatHistory } from "../api/assistant";

export function useChatHistory() {
  return useQuery({
    queryKey: ["assistant", "messages"],
    queryFn: getChatHistory,
  });
}
