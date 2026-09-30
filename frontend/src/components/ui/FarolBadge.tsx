import Icon from "./Icon";

export type FarolLevel = "excelente" | "atencao" | "prioritario" | "critico";

interface Variant {
  label: string;
  fg: string;
  bg: string;
  bd: string;
  icon: string;
}

const VARIANTS: Record<FarolLevel, Variant> = {
  excelente: { label: "Excelente", fg: "#0B6B3A", bg: "#E4F4EA", bd: "#8FD1AC", icon: "check_circle" },
  atencao: { label: "Atenção", fg: "#7A5600", bg: "#FFF3CC", bd: "#E6C766", icon: "warning" },
  prioritario: {
    label: "Desenvolvimento Prioritário",
    fg: "#A44100",
    bg: "#FFE6D2",
    bd: "#F0AE7C",
    icon: "flag",
  },
  critico: { label: "Desenvolvimento Crítico", fg: "#A10019", bg: "#FDE7EA", bd: "#EF9A9A", icon: "cancel" },
};

export function farolLevelForScore(score: number): FarolLevel {
  if (score >= 85) return "excelente";
  if (score >= 70) return "atencao";
  if (score >= 50) return "prioritario";
  return "critico";
}

interface Props {
  level: FarolLevel;
}

export default function FarolBadge({ level }: Props) {
  const v = VARIANTS[level];
  return (
    <span className="ui-farol-badge" style={{ background: v.bg, color: v.fg, borderColor: v.bd }}>
      <Icon name={v.icon} size={16} filled />
      {v.label}
    </span>
  );
}
