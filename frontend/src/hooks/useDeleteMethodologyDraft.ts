import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteMethodologyDraft } from "../api/methodology";

export function useDeleteMethodologyDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMethodologyDraft(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["methodology"] });
    },
  });
}
