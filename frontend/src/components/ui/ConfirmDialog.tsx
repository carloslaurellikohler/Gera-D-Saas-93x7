import { useEffect, useRef, type KeyboardEvent } from "react";
import Icon from "./Icon";

export type ConfirmTone = "default" | "danger";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: ConfirmTone;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  tone = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    (tone === "danger" ? cancelRef.current : confirmRef.current)?.focus();
  }, [open, tone]);

  if (!open) return null;

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onCancel();
      return;
    }
    if (e.key === "Tab") {
      const first = tone === "danger" ? cancelRef.current : confirmRef.current;
      const last = tone === "danger" ? confirmRef.current : cancelRef.current;
      if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      } else if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      }
    }
  };

  return (
    <div
      className="ui-confirm-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        className="ui-confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ui-confirm-dialog-title"
        aria-describedby={description ? "ui-confirm-dialog-description" : undefined}
        onKeyDown={handleKeyDown}
      >
        <div className="ui-confirm-dialog-header">
          <span
            className={`ui-confirm-dialog-icon ui-confirm-dialog-icon-${tone}`}
            aria-hidden="true"
          >
            <Icon name={tone === "danger" ? "warning" : "help"} size={22} filled />
          </span>
          <h2 id="ui-confirm-dialog-title" className="ui-confirm-dialog-title">
            {title}
          </h2>
        </div>
        {description && (
          <p id="ui-confirm-dialog-description" className="ui-confirm-dialog-description">
            {description}
          </p>
        )}
        <div className="ui-confirm-dialog-actions">
          <button type="button" ref={cancelRef} className="btn btn-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            ref={confirmRef}
            className={tone === "danger" ? "btn btn-danger" : "btn btn-primary"}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
