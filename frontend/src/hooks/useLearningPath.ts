import { useQuery } from "@tanstack/react-query";
import { getLearningPath } from "../api/learningPaths";

export function useLearningPath(id: string) {
  return useQuery({
    queryKey: ["learning-path", id],
    queryFn: () => getLearningPath(id),
    enabled: Boolean(id),
  });
}
