import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateMethodologyDraft } from "../api/methodology";
import type { MethodologyDraftPayload } from "../types/methodology";

export function useUpdateMethodologyDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: MethodologyDraftPayload }) =>
      updateMethodologyDraft(id, payload),
    onSuccess: (updated, variables) => {
      queryClient.setQueryData(["methodology", variables.id], updated);
      // A prévia do prompt é recompilada a cada salvamento; com a lista invalidada de
      // forma exata, ela precisa ser dita explicitamente.
      queryClient.invalidateQueries({
        queryKey: ["methodology", variables.id, "prompt-preview"],
      });
      return queryClient.invalidateQueries({ queryKey: ["methodology"], exact: true });
    },
  });
}
