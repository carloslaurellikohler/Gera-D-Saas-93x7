import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sendChatMessage } from "../api/assistant";

export function useSendChatMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: sendChatMessage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assistant", "messages"] });
    },
  });
}
