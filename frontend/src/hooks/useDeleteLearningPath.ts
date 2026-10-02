import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteLearningPath } from "../api/learningPaths";

export function useDeleteLearningPath() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteLearningPath,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["learning-paths"] });
      queryClient.invalidateQueries({ queryKey: ["learning-path", id] });
    },
  });
}
