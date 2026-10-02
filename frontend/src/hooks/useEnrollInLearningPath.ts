import { useMutation, useQueryClient } from "@tanstack/react-query";
import { enrollInLearningPath } from "../api/learningPaths";

export function useEnrollInLearningPath() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: enrollInLearningPath,
    onSuccess: (_data, learningPathId) => {
      queryClient.invalidateQueries({ queryKey: ["learning-paths", "enrolled"] });
      queryClient.invalidateQueries({ queryKey: ["learning-path", learningPathId] });
    },
  });
}
