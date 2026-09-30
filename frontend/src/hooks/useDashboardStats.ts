import { useQuery } from "@tanstack/react-query";
import { getDashboardStats } from "../api/dashboard";
import type { DashboardPeriod } from "../types/dashboard";

export function useDashboardStats(period: DashboardPeriod = "6m") {
  return useQuery({
    queryKey: ["dashboard", "stats", period],
    queryFn: () => getDashboardStats(period),
  });
}
