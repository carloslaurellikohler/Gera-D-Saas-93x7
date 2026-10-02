import { useQuery } from "@tanstack/react-query";
import { listContent } from "../api/content";
import type { CriterionKey } from "../types/content";

export function useContentLibrary(criterionKey?: CriterionKey) {
  return useQuery({
    queryKey: ["content", criterionKey ?? "all"],
    queryFn: () => listContent(criterionKey),
  });
}
