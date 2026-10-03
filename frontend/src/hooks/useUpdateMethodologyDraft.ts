import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateMethodologyDraft } from "../api/methodology";
import type { MethodologyDraftPayload } from "../types/methodology";

export function useUpdateMethodologyDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: MethodologyDraftPayload }) =>
      updateMethodologyDraft(id, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["methodology"] });
      queryClient.invalidateQueries({ queryKey: ["methodology", variables.id] });
    },
  });
}
