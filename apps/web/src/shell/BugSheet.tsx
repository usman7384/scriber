import { useRef, useState, type FormEvent } from "react";
import { api } from "../api";
import { useT } from "../i18n";

interface Props {
  modelId: string;
  version: number;
  screenshot: () => string | undefined;
}

export function BugDialog({ modelId, version, screenshot }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [text, setText] = useState("");
  const [attach, setAttach] = useState(true);
  const [result, setResult] = useState<string>();
  const t = useT();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const shot = attach ? screenshot() : undefined;
    api.reportBug({ model_id: modelId, version, text, ...(shot && { screenshot: shot }) }).then(
      () => {
        setText("");
        setResult(t.bug.saved);
      },
      (err: Error) => setResult(t.bug.failed(err.message)),
    );
  };

  return (
    <>
      <button type="button" className="ghost" onClick={() => dialog.current?.showModal()}>
        {t.bug.open}
      </button>
      <dialog ref={dialog} aria-labelledby="bug-title">
        <form onSubmit={submit} className="stack">
          <h2 id="bug-title">{t.bug.open}</h2>
          <label htmlFor="bug-text">{t.bug.question}</label>
          <textarea id="bug-text" rows={5} value={text} onChange={(e) => setText(e.target.value)} required />
          <label className="toggle">
            <input type="checkbox" checked={attach} onChange={(e) => setAttach(e.target.checked)} />
            {t.bug.attach}
          </label>
          {result && <p role="status">{result}</p>}
          <div className="row">
            <button type="button" className="secondary" onClick={() => dialog.current?.close()}>
              {t.close}
            </button>
            <button type="submit" className="primary push">
              {t.bug.send}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
