import { useMutation, useQueryClient } from "@tanstack/react-query";
import { recalculateAiModelPrice } from "../api/aiCosts";

export function useRecalculateAiModelPrice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: recalculateAiModelPrice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-costs"] });
    },
  });
}
