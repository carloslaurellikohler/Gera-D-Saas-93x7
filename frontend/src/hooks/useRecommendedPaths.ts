import { useQuery } from "@tanstack/react-query";
import { getRecommendedLearningPaths } from "../api/learningPaths";

export function useRecommendedPaths() {
  return useQuery({
    queryKey: ["learning-paths", "recommended"],
    queryFn: getRecommendedLearningPaths,
  });
}
