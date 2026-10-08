import type { AnalysisStatus } from "../../types/analysis";
import { formatStatus } from "../../lib/format";
import Icon from "./Icon";

interface Variant {
  bg: string;
  fg: string;
  bd: string;
  dashed?: boolean;
  icon: string;
}

const SPINNING_STATUSES: AnalysisStatus[] = ["TRANSCRIBING", "ANALYZING", "GENERATING_REPORTS"];

const VARIANTS: Record<AnalysisStatus, Variant> = {
  CREATED: { bg: "#ECEEF2", fg: "#333846", bd: "#C4C9D3", icon: "draft" },
  UPLOADED: { bg: "#ECEEF2", fg: "#333846", bd: "#C4C9D3", icon: "upload" },
  TRANSCRIBING: { bg: "#E3F2FD", fg: "#0B4F91", bd: "#90CAF9", icon: "progress_activity" },
  TRANSCRIBED: { bg: "#E3F2FD", fg: "#0B4F91", bd: "#90CAF9", icon: "subtitles" },
  ANALYZING: { bg: "#EEE8F8", fg: "#4B2E79", bd: "#C9B8E6", icon: "progress_activity" },
  GENERATING_REPORTS: { bg: "#EEE8F8", fg: "#4B2E79", bd: "#C9B8E6", icon: "progress_activity" },
  COMPLETED: { bg: "#E4E5EE", fg: "#00003C", bd: "#00003C", icon: "task_alt" },
  FAILED: { bg: "#FFFFFF", fg: "#12141C", bd: "#12141C", dashed: true, icon: "error" },
};

interface Props {
  status: AnalysisStatus;
}

export default function StatusBadge({ status }: Props) {
  const v = VARIANTS[status];
  return (
    <span
      className="ui-status-badge"
      style={{
        background: v.bg,
        color: v.fg,
        borderColor: v.bd,
        borderStyle: v.dashed ? "dashed" : "solid",
      }}
    >
      <Icon name={v.icon} size={15} spin={SPINNING_STATUSES.includes(status)} />
      {formatStatus(status)}
    </span>
  );
}
