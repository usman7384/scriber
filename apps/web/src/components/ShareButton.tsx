import { useState } from "react";
import { api } from "../api";
import { useT } from "../i18n";

export function ShareButton({ modelId, version }: { modelId: string; version: number }) {
  const [share, setShare] = useState<{ id: string; url: string }>();
  const [note, setNote] = useState<string>();
  const [error, setError] = useState<string>();
  const t = useT().share;
  const fail = (e: Error) => setError(e.message);
  const create = () =>
    api.share(modelId, version).then((s) => {
      setNote(undefined);
      setShare({ id: s.id, url: new URL(`/shared/${s.id}`, location.href).href });
    }, fail);
  const revoke = (id: string) =>
    api.revokeShare(id).then(() => {
      setShare(undefined);
      setNote(t.revoked);
    }, fail);
  return (
    <span className="row">
      <button type="button" className="secondary" onClick={create}>
        {t.share}
      </button>
      {share && (
        <>
          <input readOnly value={share.url} aria-label={t.link} onFocus={(e) => e.target.select()} />
          <button
            type="button"
            className="secondary"
            onClick={() => navigator.clipboard.writeText(share.url)}
          >
            {t.copy}
          </button>
          <button type="button" className="secondary" onClick={() => revoke(share.id)}>
            {t.revoke}
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
