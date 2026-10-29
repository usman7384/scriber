import { api } from "../api";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";
import { useT } from "../i18n";

export function FactList({ projectId, fileId }: { projectId: string; fileId: string }) {
  const facts = useResource(`facts:${fileId}`, () => api.facts(projectId, fileId));
  const t = useT().context;
  if (!facts.data) return <Pending error={facts.error} />;
  if (facts.data.length === 0) return <p className="src-empty">{t.noFacts}</p>;
  return (
    <ul className="src-facts" aria-label={t.facts}>
      {facts.data.map((f) => (
        <li key={f.id}>
          <span className="mono src-fact">
            {f.name} = {String(f.value)}
            {f.unit && ` ${f.unit}`}
            {f.tol != null && ` ± ${String(f.tol)}`}
          </span>
          <span className="src-meta">
            {f.kind} · <span className="mono">{`p${f.page}:l${f.line}`}</span>
          </span>
          <q>{f.text}</q>
        </li>
      ))}
    </ul>
  );
}
