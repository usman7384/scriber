import { useState, type FormEvent } from "react";

interface Props {
  target?: string | undefined;
  busy: boolean;
  onClearTarget: () => void;
  onRefine: (instruction: string) => void;
}

export function RefineBox({ target, busy, onClearTarget, onRefine }: Props) {
  const [text, setText] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onRefine(text.trim());
    setText("");
  };
  return (
    <form className="refine" onSubmit={submit} aria-label="Refine">
      <span className="chip">
        Target: {target ?? "Entire object"}
        {target && (
          <button type="button" className="link" onClick={onClearTarget}>
            Clear
          </button>
        )}
      </span>
      <label className="sr-only" htmlFor="refine">
        Change request
      </label>
      <input
        id="refine"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. make it 10 mm thicker"
      />
      <button type="submit" className="primary" disabled={busy || !text.trim()}>
        Refine
      </button>
    </form>
  );
}
