import { useQuery } from "@tanstack/react-query";
import { getAiCostSummary } from "../api/aiCosts";
import type { AiCostPeriod } from "../types/aiCost";

export function useAiCostSummary(period: AiCostPeriod = "30d") {
  return useQuery({
    queryKey: ["ai-costs", "summary", period],
    queryFn: () => getAiCostSummary(period),
  });
}
