import { apiGet } from "./client";
import type { DashboardPeriod, DashboardStatsResponse } from "../types/dashboard";

export function getDashboardStats(period: DashboardPeriod = "6m") {
  return apiGet<DashboardStatsResponse>(`/dashboard/stats?period=${period}`);
}
