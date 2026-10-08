import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateAiCostConfig } from "../api/aiCosts";

export function useUpdateAiCostConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateAiCostConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-costs"] });
    },
  });
}
