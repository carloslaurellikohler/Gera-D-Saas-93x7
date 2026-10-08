import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createAiModelPrice, updateAiModelPrice } from "../api/aiCosts";
import type { AiModelPricePayload } from "../types/aiCost";

interface SaveArgs {
  id?: string;
  payload: AiModelPricePayload;
}

export function useSaveAiModelPrice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: SaveArgs) =>
      id ? updateAiModelPrice(id, payload) : createAiModelPrice(payload),
    onSuccess: () => {
      // Invalida a raiz: mudar preço afeta tanto a lista quanto o summary (um preço novo
      // muda quais chamadas futuras ficam sem preço).
      queryClient.invalidateQueries({ queryKey: ["ai-costs"] });
    },
  });
}
