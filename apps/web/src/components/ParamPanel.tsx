import { useEffect, useEffectEvent, useState, type FormEvent } from "react";
import type { Param } from "../api";
import { ParamRow } from "./ParamRow";

const DEBOUNCE_MS = 400;

interface Props {
  params: Param[];
  busy: boolean;
  onApply: (values: Record<string, number>) => void;
}

export function ParamPanel({ params, busy, onApply }: Props) {
  // Drafts belong to one params list; a new version or reload starts clean.
  const [edit, setEdit] = useState({ of: params, drafts: {} as Record<string, string> });
  const [instant, setInstant] = useState(false);
  const drafts = edit.of === params ? edit.drafts : {};
  const changes = Object.fromEntries(
    params.flatMap((p) => {
      const v = Number(drafts[p.name] ?? p.value);
      return Number.isFinite(v) && v !== p.value ? [[p.name, v]] : [];
    }),
  );
  const dirty = Object.keys(changes).length > 0;
  const apply = () => dirty && onApply(changes);

  const flush = useEffectEvent(apply);
  useEffect(() => {
    if (!instant) return;
    const t = setTimeout(flush, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [instant, edit]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    apply();
  };

  if (params.length === 0) return <p className="muted">This version has no parameters.</p>;
  return (
    <form className="params" onSubmit={submit} aria-label="Parameters">
      <label className="toggle">
        <input type="checkbox" checked={instant} onChange={(e) => setInstant(e.target.checked)} />
        Apply instantly
      </label>
      {params.map((p) => (
        <ParamRow
          key={p.name}
          param={p}
          draft={drafts[p.name] ?? String(p.value)}
          onChange={(d) => setEdit({ of: params, drafts: { ...drafts, [p.name]: d } })}
        />
      ))}
      {!instant && (
        <button type="submit" className="primary" disabled={!dirty || busy}>
          Apply
        </button>
      )}
    </form>
  );
}
