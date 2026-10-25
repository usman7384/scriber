import { useRef, useState, type FormEvent } from "react";
import { api } from "../api";

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

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const shot = attach ? screenshot() : undefined;
    api.reportBug({ model_id: modelId, version, text, ...(shot && { screenshot: shot }) }).then(
      () => {
        setText("");
        setResult("Thanks, the report was saved.");
      },
      (err: Error) => setResult(`Could not send the report: ${err.message}`),
    );
  };

  return (
    <>
      <button type="button" className="ghost" onClick={() => dialog.current?.showModal()}>
        Report a bug
      </button>
      <dialog ref={dialog} aria-labelledby="bug-title">
        <form onSubmit={submit} className="stack">
          <h2 id="bug-title">Report a bug</h2>
          <label htmlFor="bug-text">What went wrong?</label>
          <textarea id="bug-text" rows={5} value={text} onChange={(e) => setText(e.target.value)} required />
          <label className="toggle">
            <input type="checkbox" checked={attach} onChange={(e) => setAttach(e.target.checked)} />
            Attach a screenshot of the viewer
          </label>
          {result && <p role="status">{result}</p>}
          <div className="row">
            <button type="button" className="secondary" onClick={() => dialog.current?.close()}>
              Close
            </button>
            <button type="submit" className="primary push">
              Send
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
