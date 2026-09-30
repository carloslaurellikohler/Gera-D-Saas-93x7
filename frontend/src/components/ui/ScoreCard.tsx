import FarolBadge, { farolLevelForScore } from "./FarolBadge";

const SOLID: Record<string, string> = {
  excelente: "#0F7A45",
  atencao: "#A87800",
  prioritario: "#C95800",
  critico: "#B00020",
};

const FG: Record<string, string> = {
  excelente: "#0B6B3A",
  atencao: "#7A5600",
  prioritario: "#A44100",
  critico: "#A10019",
};

interface Props {
  label: string;
  sub?: string;
  score: number;
  size?: "md" | "lg";
}

export default function ScoreCard({ label, sub, score, size = "md" }: Props) {
  const level = farolLevelForScore(score);

  return (
    <div className="ui-score-card">
      <div className="ui-score-card-head">
        <span>{label}</span>
        {sub && <span className="ui-score-card-sub">{sub}</span>}
      </div>
      <div className="ui-score-card-number">
        <span style={{ fontSize: size === "lg" ? 64 : 40, color: FG[level] }}>{score}</span>
        <span className="ui-score-card-max">/100</span>
      </div>
      <div className="ui-score-card-bar">
        <div style={{ width: `${score}%`, background: SOLID[level] }} />
        <span style={{ left: "50%" }} />
        <span style={{ left: "70%" }} />
        <span style={{ left: "85%" }} />
      </div>
      <FarolBadge level={level} />
    </div>
  );
}
