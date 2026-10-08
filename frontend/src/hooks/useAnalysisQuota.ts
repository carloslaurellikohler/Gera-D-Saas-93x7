import { useQuery } from "@tanstack/react-query";
import { getAnalysisQuota } from "../api/analyses";

export function useAnalysisQuota(ownerId: string | undefined, enabled: boolean = true) {
  return useQuery({
    queryKey: ["analyses", "quota", ownerId ?? "self"],
    queryFn: () => getAnalysisQuota(ownerId),
    enabled,
  });
}
