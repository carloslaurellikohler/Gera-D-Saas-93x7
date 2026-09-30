import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createAnalysis } from "../api/analyses";

export function useCreateAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAnalysis,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
    },
  });
}
