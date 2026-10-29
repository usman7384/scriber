import { useState } from "react";
import { api } from "../api";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { Popover } from "../ui/Popover";

export function ShareButton({ modelId, version }: { modelId: string; version: number }) {
  const [share, setShare] = useState<{ id: string; url: string }>();
  const [note, setNote] = useState<string>();
  const [error, setError] = useState<string>();
  const t = useT().share;
  const fail = (e: Error) => setError(e.message);
  const create = () => {
    setNote(undefined);
    setError(undefined);
    api.share(modelId, version).then((s) => {
      setShare({ id: s.id, url: new URL(`/shared/${s.id}`, location.href).href });
    }, fail);
  };
  const revoke = (id: string) =>
    api.revokeShare(id).then(() => {
      setShare(undefined);
      setNote(t.revoked);
    }, fail);
  return (
    <Popover
      label={t.share}
      align="end"
      trigger={(p) => (
        <Button {...p} icon="globe" onClick={() => !p["aria-expanded"] && create()}>
          <span className="ws-wide">{t.share}</span>
        </Button>
      )}
    >
      <div className="ws-share">
        {share && (
          <div className="ws-share-row">
            <input
              readOnly
              className="mono"
              value={share.url}
              aria-label={t.link}
              onFocus={(e) => e.target.select()}
            />
            <Button onClick={() => void navigator.clipboard.writeText(share.url)}>{t.copy}</Button>
            <Button variant="ghost" onClick={() => void revoke(share.id)}>
              {t.revoke}
            </Button>
          </div>
        )}
        {!share && !note && !error && <p className="ws-muted">{t.creating}</p>}
        {note && <p role="status">{note}</p>}
        {error && (
          <p role="alert" className="ws-error">
            {error}
          </p>
        )}
      </div>
    </Popover>
  );
}
