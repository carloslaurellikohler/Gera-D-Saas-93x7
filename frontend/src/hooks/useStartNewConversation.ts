import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startNewConversation } from "../api/assistant";

export function useStartNewConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: startNewConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assistant", "messages"] });
    },
  });
}
