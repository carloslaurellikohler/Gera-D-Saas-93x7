import type { ReactNode } from "react";
import Icon from "./Icon";

interface Props {
  icon: string;
  title: string;
  description?: string;
  children?: ReactNode;
}

export default function EmptyState({ icon, title, description, children }: Props) {
  return (
    <div className="ui-empty-state">
      <span className="ui-empty-state-icon">
        <Icon name={icon} size={44} />
      </span>
      <span className="ui-empty-state-title">{title}</span>
      {description && <span className="ui-empty-state-description">{description}</span>}
      {children}
    </div>
  );
}
