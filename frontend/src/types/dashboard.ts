export type DashboardPeriod = "30d" | "90d" | "6m";

export interface VolumeByStatus {
  status: string;
  count: number;
}

export interface FarolDistributionItem {
  label: string;
  level: string;
  count: number;
  pct: string;
}

export interface TrendPoint {
  period_start: string;
  count: number;
  avg_score: number | null;
}

export interface TeamBoardRow {
  user_id: string;
  name: string;
  count: number;
  avg_score: number | null;
  level: string | null;
  trend: "up" | "down" | "flat" | null;
}

export interface DashboardStatsResponse {
  period: DashboardPeriod;
  volume_by_status: VolumeByStatus[];
  farol_distribution: FarolDistributionItem[];
  trend: TrendPoint[];
  team_board: TeamBoardRow[] | null;
}
