import { useState } from "react";
import { api } from "../api";

export function ShareButton({ modelId, version }: { modelId: string; version: number }) {
  const [share, setShare] = useState<{ id: string; url: string }>();
  const [note, setNote] = useState<string>();
  const [error, setError] = useState<string>();
  const fail = (e: Error) => setError(e.message);
  const create = () =>
    api.share(modelId, version).then((s) => {
      setNote(undefined);
      setShare({ id: s.id, url: new URL(`/shared/${s.id}`, location.href).href });
    }, fail);
  const revoke = (id: string) =>
    api.revokeShare(id).then(() => {
      setShare(undefined);
      setNote("Link revoked");
    }, fail);
  return (
    <span className="row">
      <button type="button" className="secondary" onClick={create}>
        Share
      </button>
      {share && (
        <>
          <input readOnly value={share.url} aria-label="Share link" onFocus={(e) => e.target.select()} />
          <button
            type="button"
            className="secondary"
            onClick={() => navigator.clipboard.writeText(share.url)}
          >
            Copy
          </button>
          <button type="button" className="secondary" onClick={() => revoke(share.id)}>
            Revoke
          </button>
        </>
      )}
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
