import Icon from "./Icon";

export type TrailStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";

interface Variant {
  bg: string;
  fg: string;
  bd: string;
  icon: string;
  label: string;
}

const VARIANTS: Record<TrailStatus, Variant> = {
  NOT_STARTED: { bg: "#ECEEF2", fg: "#333846", bd: "#C4C9D3", icon: "radio_button_unchecked", label: "Não iniciada" },
  IN_PROGRESS: { bg: "#E3F2FD", fg: "#0B4F91", bd: "#90CAF9", icon: "progress_activity", label: "Em andamento" },
  COMPLETED: { bg: "#E4E5EE", fg: "#00003C", bd: "#00003C", icon: "task_alt", label: "Concluída" },
};

interface Props {
  status: TrailStatus;
}

export default function TrailStatusBadge({ status }: Props) {
  const v = VARIANTS[status];
  return (
    <span className="ui-status-badge" style={{ background: v.bg, color: v.fg, borderColor: v.bd }}>
      <Icon name={v.icon} size={15} />
      {v.label}
    </span>
  );
}
