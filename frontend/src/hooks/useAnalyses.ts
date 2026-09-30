import { useQuery } from "@tanstack/react-query";
import { listAnalyses } from "../api/analyses";
import type { AnalysisStatus } from "../types/analysis";

export function useAnalyses(status?: AnalysisStatus) {
  return useQuery({
    queryKey: ["analyses", status ?? "all"],
    queryFn: () => listAnalyses(status),
  });
}
