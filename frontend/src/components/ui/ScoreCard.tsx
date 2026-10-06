import FarolBadge, { type FarolLevel } from "./FarolBadge";

const SOLID: Record<string, string> = {
  excelente: "#0F7A45",
  atencao: "#A87800",
  prioritario: "#C95800",
  critico: "#B00020",
  outro: "var(--gerad-navy)",
};

const FG: Record<string, string> = {
  excelente: "#0B6B3A",
  atencao: "#7A5600",
  prioritario: "#A44100",
  critico: "#A10019",
  outro: "var(--gerad-navy)",
};

interface Props {
  label: string;
  sub?: string;
  score: number;
  level?: FarolLevel;
  size?: "md" | "lg";
}

export default function ScoreCard({ label, sub, score, level, size = "md" }: Props) {
  const color = level ? level : "outro";

  return (
    <div className="ui-score-card">
      <div className="ui-score-card-head">
        <span>{label}</span>
        {sub && <span className="ui-score-card-sub">{sub}</span>}
      </div>
      <div className="ui-score-card-number">
        <span style={{ fontSize: size === "lg" ? 64 : 40, color: FG[color] }}>{score}</span>
        <span className="ui-score-card-max">/10</span>
      </div>
      <div className="ui-score-card-bar">
        <div style={{ width: `${(score / 10) * 100}%`, background: SOLID[color] }} />
        <span style={{ left: "50%" }} />
        <span style={{ left: "70%" }} />
        <span style={{ left: "85%" }} />
      </div>
      {level && <FarolBadge level={level} />}
    </div>
  );
}
