import { useQuery } from "@tanstack/react-query";
import { listEnrolledLearningPaths } from "../api/learningPaths";

export function useEnrolledLearningPaths() {
  return useQuery({
    queryKey: ["learning-paths", "enrolled"],
    queryFn: listEnrolledLearningPaths,
  });
}
