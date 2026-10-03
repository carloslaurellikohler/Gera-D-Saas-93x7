import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createMethodologyDraft } from "../api/methodology";

export function useCreateMethodologyDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fromId?: string) => createMethodologyDraft(fromId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["methodology"] });
    },
  });
}
