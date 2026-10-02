import { useMutation, useQueryClient } from "@tanstack/react-query";
import { completeLearningPathItem, uncompleteLearningPathItem } from "../api/learningPaths";

export function useCompleteLearningPathItem(learningPathId: string) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["learning-path", learningPathId] });
    queryClient.invalidateQueries({ queryKey: ["learning-paths", "enrolled"] });
  };
  const complete = useMutation({
    mutationFn: (itemId: string) => completeLearningPathItem(learningPathId, itemId),
    onSuccess: invalidate,
  });
  const uncomplete = useMutation({
    mutationFn: (itemId: string) => uncompleteLearningPathItem(learningPathId, itemId),
    onSuccess: invalidate,
  });
  return { complete, uncomplete };
}
