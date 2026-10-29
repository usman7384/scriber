import { useEffect, useId, useRef, type ReactNode } from "react";
import { useT } from "../i18n";
import { IconButton } from "./IconButton";
import "./ui.css";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  footer?: ReactNode;
  children: ReactNode;
}

// A modal <dialog>: the browser traps focus, closes on Esc and returns focus to the opener.
export function Sheet({ open, onClose, title, footer, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  const t = useT();
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      className="ui-sheet"
      aria-labelledby={id}
      onClose={() => open && onClose()}
      onClick={(e) => e.target === e.currentTarget && e.currentTarget.close()}
    >
      <header className="ui-sheet-head">
        <h2 id={id}>{title}</h2>
        <IconButton icon="close" label={t.close} onClick={() => ref.current?.close()} />
      </header>
      <div className="ui-sheet-body">{children}</div>
      {footer && <footer className="ui-sheet-foot">{footer}</footer>}
    </dialog>
  );
}
