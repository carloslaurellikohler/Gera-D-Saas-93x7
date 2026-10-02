import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteContent } from "../api/content";

export function useDeleteContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteContent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
    },
  });
}
