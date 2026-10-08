import type { CSSProperties } from "react";

interface Props {
  name: string;
  size?: number;
  filled?: boolean;
  color?: string;
  className?: string;
  style?: CSSProperties;
  spin?: boolean;
}

export default function Icon({ name, size = 20, filled = false, color, className, style, spin = false }: Props) {
  return (
    <span
      aria-hidden="true"
      className={`material-symbols-rounded${spin ? " ui-icon-spin" : ""}${className ? ` ${className}` : ""}`}
      style={{
        fontSize: size,
        color,
        fontVariationSettings: filled ? "'FILL' 1" : undefined,
        ...style,
      }}
    >
      {name}
    </span>
  );
}
