interface Props {
  percent: number;
}

export default function ProgressBar({ percent }: Props) {
  const clamped = Math.min(100, Math.max(0, percent));
  return (
    <div
      className="ui-progress-bar"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="ui-progress-bar-fill" style={{ width: `${clamped}%` }} />
    </div>
  );
}
