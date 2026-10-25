import { api } from "../api";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";

export function FactsList({ projectId, fileId }: { projectId: string; fileId: string }) {
  const facts = useResource(`facts:${fileId}`, () => api.facts(projectId, fileId));
  if (!facts.data) return <Pending error={facts.error} />;
  if (facts.data.length === 0) return <p className="muted">No facts extracted from this file.</p>;
  return (
    <ul className="list" aria-label="Facts">
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
