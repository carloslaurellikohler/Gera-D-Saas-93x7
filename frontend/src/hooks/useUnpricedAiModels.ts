import { useQuery } from "@tanstack/react-query";
import { listUnpricedAiModels } from "../api/aiCosts";

export function useUnpricedAiModels() {
  return useQuery({
    queryKey: ["ai-costs", "unpriced-models"],
    queryFn: listUnpricedAiModels,
  });
}
