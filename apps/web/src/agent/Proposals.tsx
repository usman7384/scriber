import { useState } from "react";
import { api, type Job } from "../api";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { changeText, proposedChanges } from "./diff";
import "./agent.css";

interface Props {
  modelId: string;
  onApplied: (job: Job) => void;
}

export function Proposals({ modelId, onApplied }: Props) {
  const t = useT();
  const p = t.agent.proposals;
  const [nonce, setNonce] = useState(0);
  const list = useResource(`proposals:${modelId}:${nonce}`, () => api.suggestions(modelId));
  const versions = useResource(`proposals-params:${modelId}:${nonce}`, () => api.versions(modelId));
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();
  const params = versions.data?.at(-1)?.params ?? [];
  const open = list.data?.filter((s) => s.status === "open") ?? [];

  const act = async (id: string, run: () => Promise<unknown>) => {
    setBusy(id);
    setError(undefined);
    try {
      await run();
      setNonce((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(undefined);
    }
  };
  const apply = (id: string) => act(id, () => api.acceptSuggestion(modelId, id).then(onApplied));
  const dismiss = (id: string) => act(id, () => api.ignoreSuggestion(modelId, id));

  return (
    <section className="agent-proposals" aria-label={t.suggestions.region}>
      <header className="agent-bar-row">
        <span className="eyebrow">{p.title}</span>
        <span className="agent-meta mono">{open.length}</span>
        <span className="agent-spacer" />
        <Button
          variant="ghost"
          icon="agent"
          disabled={busy !== undefined}
          onClick={() => act("ask", () => api.suggest(modelId))}
        >
          {busy === "ask" ? t.suggestions.thinking : t.suggestions.ask}
        </Button>
      </header>
      {list.data && open.length === 0 && <p className="agent-meta">{t.suggestions.none}</p>}
      <ul className="agent-proposal-list">
        {open.map((s) => (
          <li key={s.id} className="agent-proposal">
            <div className="agent-step-detail mono">
              {proposedChanges(s.change, params).map((c) => (
                <div key={c.name}>~ {changeText(c)}</div>
              ))}
            </div>
            <p className="agent-proposal-why">{s.rationale}</p>
            <div className="agent-bar-row">
              <Button variant="primary" disabled={busy !== undefined} onClick={() => void apply(s.id)}>
                {busy === s.id ? p.applying : p.apply}
              </Button>
              <Button variant="ghost" disabled={busy !== undefined} onClick={() => void dismiss(s.id)}>
                {p.dismiss}
              </Button>
            </div>
          </li>
        ))}
      </ul>
      {error && (
        <p role="alert" className="agent-error">
          {error}
        </p>
      )}
    </section>
  );
}
