import { useQuery } from "@tanstack/react-query";
import { listLearningPaths } from "../api/learningPaths";

export function useLearningPaths() {
  return useQuery({
    queryKey: ["learning-paths", "all"],
    queryFn: listLearningPaths,
  });
}
