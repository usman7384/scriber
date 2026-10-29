import { useState } from "react";
import { api } from "../api";
import { useT } from "../i18n";

export function PublishButton({ modelId, version }: { modelId: string; version: number }) {
  const [note, setNote] = useState<string>();
  const [error, setError] = useState<string>();
  const t = useT().community;
  const publish = () => {
    setError(undefined);
    api.publish(modelId, version).then(
      () => setNote(t.published),
      (e: Error) => setError(e.message),
    );
  };
  return (
    <span className="row">
      <button type="button" className="secondary" onClick={publish}>
        {t.publish}
      </button>
      {note && (
        <span role="status" className="muted small">
          {note}
        </span>
      )}
      {error && (
        <span role="alert" className="error">
          {error}
        </span>
      )}
    </span>
  );
}
