import { useId, useState } from "react";
import Icon from "./Icon";

interface Props {
  title: string;
  /** Texto curto à direita do título (ex.: o peso do critério). */
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

/**
 * Seção expansível. Nasceu na tela de metodologia: um critério da V2.1 tem definição,
 * 5 âncoras, exemplos, subdimensões e regras de elegibilidade — abrir os 6 critérios de
 * uma vez daria uma página impossível de percorrer.
 */
export default function Collapsible({ title, badge, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <div className="collapsible">
      <button
        type="button"
        className="collapsible-header"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((value) => !value)}
      >
        <Icon name={open ? "expand_more" : "chevron_right"} size={20} />
        <span className="collapsible-title">{title}</span>
        {badge ? <span className="collapsible-badge">{badge}</span> : null}
      </button>
      {open ? (
        <div className="collapsible-body" id={contentId}>
          {children}
        </div>
      ) : null}
    </div>
  );
}
