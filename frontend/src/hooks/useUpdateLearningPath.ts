import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateLearningPath } from "../api/learningPaths";
import type { UpdateLearningPathPayload } from "../types/learningPath";

export function useUpdateLearningPath() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateLearningPathPayload }) =>
      updateLearningPath(id, payload),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["learning-paths"] });
      queryClient.invalidateQueries({ queryKey: ["learning-path", id] });
    },
  });
}
