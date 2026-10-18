import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateRuntimeSettings } from "../api/runtimeSettings";
import type { RuntimeSettingsPayload } from "../types/runtimeSettings";

export function useUpdateRuntimeSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    // Arrow em vez da função direta: o react-query passa um segundo argumento de contexto
    // para a mutationFn, e a camada de api só declara o payload.
    mutationFn: (payload: RuntimeSettingsPayload) => updateRuntimeSettings(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
