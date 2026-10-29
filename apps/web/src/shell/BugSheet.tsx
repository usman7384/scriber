import { useId, useState, type FormEvent } from "react";
import { api } from "../api";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { Sheet } from "../ui/Sheet";
import type { BugTarget } from "./context";

export function BugSheet({ target, onClose }: { target: BugTarget; onClose: () => void }) {
  const [text, setText] = useState("");
  const [attach, setAttach] = useState(true);
  const [result, setResult] = useState<string>();
  const id = useId();
  const t = useT();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const shot = attach ? target.screenshot() : undefined;
    const report = { model_id: target.modelId, version: target.version, text };
    api.reportBug({ ...report, ...(shot && { screenshot: shot }) }).then(
      () => {
        setText("");
        setResult(t.bug.saved);
      },
      (err: Error) => setResult(t.bug.failed(err.message)),
    );
  };

  return (
    <Sheet
      open
      onClose={onClose}
      title={t.bug.open}
      footer={
        <Button type="submit" form={id} variant="primary" icon="send">
          {t.bug.send}
        </Button>
      }
    >
      <form id={id} onSubmit={submit} className="shell-form">
        <label htmlFor={`${id}-text`}>{t.bug.question}</label>
        <textarea
          id={`${id}-text`}
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          required
        />
        <label className="shell-check">
          <input type="checkbox" checked={attach} onChange={(e) => setAttach(e.target.checked)} />
          {t.bug.attach}
        </label>
        {result && <p role="status">{result}</p>}
      </form>
    </Sheet>
  );
}
