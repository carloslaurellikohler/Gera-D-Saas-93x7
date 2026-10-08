import { useQuery } from "@tanstack/react-query";
import { listAiCostEvents } from "../api/aiCosts";
import type { AiUsageEventFilters } from "../types/aiCost";

export function useAiCostEvents(filters: AiUsageEventFilters = {}) {
  return useQuery({
    queryKey: ["ai-costs", "events", filters],
    queryFn: () => listAiCostEvents(filters),
  });
}
