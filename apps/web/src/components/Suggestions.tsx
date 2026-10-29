import { useState } from "react";
import { api, type Job, type Param } from "../api";
import { useResource } from "../hooks";

interface Props {
  modelId: string;
  version: number;
  params: Param[];
  busy: boolean;
  onAccept: (job: Promise<Job>) => void;
}

export function Suggestions({ modelId, version, params, busy, onAccept }: Props) {
  const list = useResource(`suggestions:${modelId}:${version}`, () => api.suggestions(modelId));
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string>();
  const fail = (e: Error) => setError(e.message);
  const ask = () => {
    setAsking(true);
    api
      .suggest(modelId)
      .then(list.reload, fail)
      .finally(() => setAsking(false));
  };
  const accept = (id: string) =>
    onAccept(
      api.acceptSuggestion(modelId, id).then((job) => {
        list.reload();
        return job;
      }),
    );
  const change = (name: string, value: number) => {
    const p = params.find((x) => x.name === name);
    return `${p?.label ?? name} ${p?.value ?? "?"} → ${value} ${p?.unit ?? ""}`.trim();
  };
  const open = list.data?.filter((s) => s.status === "open") ?? [];
  return (
    <section className="stack" aria-label="Suggestions">
      <header className="row">
        <h2>Suggestions</h2>
        <button type="button" className="secondary small push" disabled={busy || asking} onClick={ask}>
          {asking ? "Thinking…" : "Suggest changes"}
        </button>
      </header>
      {open.length === 0 && <p className="muted small">No open suggestions.</p>}
      <ul className="list">
        {open.map((s) => (
          <li key={s.id} className="stack suggestion">
            <strong>
              {Object.entries(s.change)
                .map(([k, v]) => change(k, v))
                .join(", ")}
            </strong>
            <span className="muted small">{s.rationale}</span>
            <span className="row">
              <button type="button" className="primary small" disabled={busy} onClick={() => accept(s.id)}>
                Accept
              </button>
              <button
                type="button"
                className="secondary small"
                onClick={() => api.ignoreSuggestion(modelId, s.id).then(list.reload, fail)}
              >
                Ignore
              </button>
            </span>
          </li>
        ))}
      </ul>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}
