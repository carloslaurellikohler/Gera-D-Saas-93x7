import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createLearningPath } from "../api/learningPaths";

export function useCreateLearningPath() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createLearningPath,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["learning-paths"] });
    },
  });
}
