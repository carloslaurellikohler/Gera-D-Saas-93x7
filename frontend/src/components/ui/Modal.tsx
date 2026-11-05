import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import Icon from "./Icon";

export type ModalSize = "medium" | "large" | "full";

export interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  size?: ModalSize;
  /** Barra de ações fixa no rodapé. Fica fora do corpo rolável, mas dentro do focus trap. */
  footer?: ReactNode;
  /** Ações no cabeçalho, entre o título e o botão de fechar (ex.: badge de status). */
  headerActions?: ReactNode;
}

const FOCUSABLE_SELECTOR = 'input, select, textarea, button, a[href], [tabindex]:not([tabindex="-1"])';

function getFocusable(container: HTMLElement | null): HTMLElement[] {
  if (!container) return [];
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute("disabled"),
  );
}

export default function Modal({
  open,
  title,
  onClose,
  children,
  size = "medium",
  footer,
  headerActions,
}: ModalProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    getFocusable(bodyRef.current)[0]?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
      return;
    }
    if (e.key === "Tab") {
      const focusable = getFocusable(panelRef.current);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      } else if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    }
  };

  return (
    <div
      className="ui-modal-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className={`ui-modal-panel ui-modal-panel-${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
      >
        <div className="ui-modal-header">
          <h2 id={titleId} className="ui-modal-title">
            {title}
          </h2>
          {headerActions ? <div className="ui-modal-header-actions">{headerActions}</div> : null}
          <button type="button" className="ui-modal-close" aria-label="Fechar" onClick={onClose}>
            <Icon name="close" size={20} />
          </button>
        </div>
        <div ref={bodyRef} className="ui-modal-body">
          {children}
        </div>
        {footer ? <div className="ui-modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}
