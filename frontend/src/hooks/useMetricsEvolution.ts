import { useQuery } from "@tanstack/react-query";
import { getMetricsEvolution } from "../api/metrics";
import type { MetricsPeriod } from "../types/metrics";

export function useMetricsEvolution(period: MetricsPeriod = "6m") {
  return useQuery({
    queryKey: ["metrics", "evolution", period],
    queryFn: () => getMetricsEvolution(period),
  });
}
