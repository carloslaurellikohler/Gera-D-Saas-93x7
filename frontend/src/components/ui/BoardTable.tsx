import FarolBadge, { toFarolLevel } from "./FarolBadge";
import Icon from "./Icon";

export interface BoardRow {
  id: string;
  name: string;
  count: number;
  avg_score: number | null;
  level: string | null;
  trend: "up" | "down" | "flat" | null;
}

const TREND_ICON = { up: "trending_up", down: "trending_down", flat: "trending_flat" };
const TREND_COLOR = { up: "#0B6B3A", down: "#A10019", flat: "var(--content-secondary)" };

export default function BoardTable({
  title,
  nameColumnLabel,
  rows,
  emptyMessage,
}: {
  title: string;
  nameColumnLabel: string;
  rows: BoardRow[];
  emptyMessage: string;
}) {
  return (
    <div className="data-table">
      <div style={{ padding: "18px 24px" }}>
        <h3>{title}</h3>
      </div>
      <div
        className="data-table-row data-table-head"
        style={{ gridTemplateColumns: "minmax(0,1.4fr) 100px 100px 220px 110px" }}
      >
        <span>{nameColumnLabel}</span>
        <span>Análises</span>
        <span>Nota média</span>
        <span>Farol</span>
        <span>Tendência</span>
      </div>
      {rows.map((row) => (
        <div
          key={row.id}
          className="data-table-row"
          style={{ gridTemplateColumns: "minmax(0,1.4fr) 100px 100px 220px 110px" }}
        >
          <b>{row.name}</b>
          <span>{row.count}</span>
          <b>{row.avg_score ?? "—"}</b>
          {row.level ? <FarolBadge level={toFarolLevel(row.level)} /> : <span>—</span>}
          {row.trend && (
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontWeight: 600,
                color: TREND_COLOR[row.trend],
              }}
            >
              <Icon name={TREND_ICON[row.trend]} size={18} />
            </span>
          )}
        </div>
      ))}
      {rows.length === 0 && (
        <div className="data-table-row">
          <span className="page-subtitle">{emptyMessage}</span>
        </div>
      )}
    </div>
  );
}
