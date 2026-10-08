import { useQuery } from "@tanstack/react-query";
import { getAiCostConfig } from "../api/aiCosts";

export function useAiCostConfig() {
  return useQuery({ queryKey: ["ai-costs", "config"], queryFn: getAiCostConfig });
}
