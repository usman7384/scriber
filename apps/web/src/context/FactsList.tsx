import { api } from "../api";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";
import { useT } from "../i18n";

export function FactsList({ projectId, fileId }: { projectId: string; fileId: string }) {
  const facts = useResource(`facts:${fileId}`, () => api.facts(projectId, fileId));
  const t = useT().context;
  if (!facts.data) return <Pending error={facts.error} />;
  if (facts.data.length === 0) return <p className="muted">{t.noFacts}</p>;
  return (
    <ul className="list" aria-label={t.facts}>
      {facts.data.map((f) => (
        <li key={f.id}>
          <strong>{f.name}</strong> {String(f.value)}
          {f.unit && ` ${f.unit}`}
          {f.tol != null && ` ± ${String(f.tol)}`}
          <span className="muted small">
            {" "}
            p{f.page}:l{f.line} · {f.kind}
          </span>
          <p className="muted small">“{f.text}”</p>
        </li>
      ))}
    </ul>
  );
}
