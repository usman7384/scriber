import { useState, type FormEvent } from "react";
import { useT } from "../i18n";

interface Props {
  target?: string | undefined;
  busy: boolean;
  onClearTarget: () => void;
  onRefine: (instruction: string) => void;
}

export function RefineBox({ target, busy, onClearTarget, onRefine }: Props) {
  const [text, setText] = useState("");
  const t = useT();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onRefine(text.trim());
    setText("");
  };
  return (
    <form className="refine" onSubmit={submit} aria-label={t.refine.form}>
      <span className="chip">
        {t.refine.target} {target ?? t.refine.whole}
        {target && (
          <button type="button" className="link" onClick={onClearTarget}>
            {t.clear}
          </button>
        )}
      </span>
      <label className="sr-only" htmlFor="refine">
        {t.refine.label}
      </label>
      <input
        id="refine"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t.refine.placeholder}
      />
      <button type="submit" className="primary" disabled={busy || !text.trim()}>
        {t.refine.submit}
      </button>
    </form>
  );
}
