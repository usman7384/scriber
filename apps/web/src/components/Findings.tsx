import type { Check, Finding } from "../api";

export function Findings({ checks, findings }: { checks: Check[]; findings: Finding[] }) {
  return (
    <div className="stack" aria-label="Checks and findings">
      <h3>Requirement checks</h3>
      {checks.length === 0 && <p className="muted">No requirement checks.</p>}
      <ul className="list">
        {checks.map((c, i) => (
          <li key={i} className="row">
            <span className={`badge ${c.passed ? "done" : "failed"}`}>{c.passed ? "pass" : "fail"}</span>
            <span>{c.description}</span>
            {c.actual !== null && <span className="muted small push">{String(c.actual)}</span>}
          </li>
        ))}
      </ul>
      <h3>Manufacturability</h3>
      {findings.length === 0 && <p className="muted">No findings.</p>}
      <ul className="list">
        {findings.map((f, i) => (
          <li key={i} className={`finding ${f.severity}`}>
            <span className={`badge ${f.severity}`}>{f.severity}</span> {f.message}
            {f.suggestion && <p className="muted small">Suggestion: {f.suggestion}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
