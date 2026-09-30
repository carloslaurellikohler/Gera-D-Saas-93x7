import { useQuery } from "@tanstack/react-query";
import { getAnalysisStatus } from "../api/analyses";
import type { AnalysisStatus } from "../types/analysis";

const TERMINAL_STATUSES: AnalysisStatus[] = ["COMPLETED", "FAILED"];
const POLL_INTERVAL_MS = 2000;

export function useAnalysisStatus(id: string) {
  return useQuery({
    queryKey: ["analysis-status", id],
    queryFn: () => getAnalysisStatus(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.includes(status)) {
        return false;
      }
      return POLL_INTERVAL_MS;
    },
  });
}
