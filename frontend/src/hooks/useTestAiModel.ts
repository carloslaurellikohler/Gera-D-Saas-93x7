import { useMutation } from "@tanstack/react-query";
import { testAiModel } from "../api/runtimeSettings";
import type { ModelTestPayload } from "../types/runtimeSettings";

/** Sem invalidação: o teste não muda estado no servidor, só valida o nome digitado. */
export function useTestAiModel() {
  return useMutation({
    mutationFn: (payload: ModelTestPayload) => testAiModel(payload),
  });
}
