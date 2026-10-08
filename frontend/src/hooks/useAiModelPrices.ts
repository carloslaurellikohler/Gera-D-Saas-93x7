import { useQuery } from "@tanstack/react-query";
import { listAiModelPrices } from "../api/aiCosts";

export function useAiModelPrices() {
  return useQuery({ queryKey: ["ai-costs", "prices"], queryFn: listAiModelPrices });
}
