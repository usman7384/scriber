import { useEffect, useEffectEvent, useState, type FormEvent } from "react";
import type { Param } from "../../api";
import { useT } from "../../i18n";
import { Button } from "../../ui/Button";
import { numberOf, outOfBounds } from "./bounds";
import { ParamRow } from "./ParamRow";

const DEBOUNCE_MS = 400;

interface Props {
  params: Param[];
  busy: boolean;
  pinned?: string | undefined;
  sourcesHref?: string | undefined;
  onApply: (values: Record<string, number>) => void;
}

export function ParamPanel({ params, busy, pinned, sourcesHref, onApply }: Props) {
  // Drafts belong to one params list; a new version or reload starts clean.
  const [edit, setEdit] = useState({ of: params, drafts: {} as Record<string, string> });
  const [live, setLive] = useState(false);
  const t = useT();
  const drafts = edit.of === params ? edit.drafts : {};
  const changes = Object.fromEntries(
    params.flatMap((p) => {
      const v = numberOf(drafts[p.name] ?? String(p.value));
      return Number.isFinite(v) && v !== p.value ? [[p.name, v]] : [];
    }),
  );
  const count = Object.keys(changes).length;
  const valid = params.every((p) => changes[p.name] === undefined || !outOfBounds(p, changes[p.name] ?? 0));
  const apply = () => count > 0 && valid && onApply(changes);

  const flush = useEffectEvent(apply);
  useEffect(() => {
    if (!live) return;
    const timer = setTimeout(flush, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [live, edit]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    apply();
  };

  if (params.length === 0) return <p className="ws-muted">{t.params.none}</p>;
  const ordered = [...params].sort((a, b) => Number(b.name === pinned) - Number(a.name === pinned));
  return (
    <form className="ws-params" onSubmit={submit} aria-label={t.params.form}>
      <div className="ws-section-head">
        <h3 className="eyebrow">{pinned ? t.params.driving : t.params.form}</h3>
        <label className="ws-live">
          {t.params.live}
          <input
            type="checkbox"
            role="switch"
            aria-label={t.params.instant}
            checked={live}
            onChange={(e) => setLive(e.target.checked)}
          />
        </label>
      </div>
      {ordered.map((p) => (
        <ParamRow
          key={p.name}
          param={p}
          pinned={p.name === pinned}
          sourcesHref={sourcesHref}
          draft={drafts[p.name] ?? String(p.value)}
          onChange={(d) => setEdit({ of: params, drafts: { ...drafts, [p.name]: d } })}
        />
      ))}
      {!live && (
        <div className="ws-params-foot">
          <Button type="submit" variant="primary" disabled={count === 0 || !valid || busy}>
            {busy ? t.params.applying : count > 0 ? t.params.applyN(count) : t.apply}
          </Button>
          {count > 0 && (
            <Button variant="ghost" onClick={() => setEdit({ of: params, drafts: {} })}>
              {t.params.reset}
            </Button>
          )}
        </div>
      )}
    </form>
  );
}
