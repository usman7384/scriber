import type { Check, Finding } from "../api";
import { useT } from "../i18n";

export function Findings({ checks, findings }: { checks: Check[]; findings: Finding[] }) {
  const t = useT();
  return (
    <div className="stack" aria-label={t.findings.region}>
      <h3>{t.findings.checks}</h3>
      {checks.length === 0 && <p className="muted">{t.findings.noChecks}</p>}
      <ul className="list">
        {checks.map((c, i) => (
          <li key={i} className="row">
            <span className={`badge ${c.passed ? "done" : "failed"}`}>
              {c.passed ? t.status.pass : t.status.fail}
            </span>
            <span>{c.description}</span>
            {c.actual !== null && <span className="muted small push">{String(c.actual)}</span>}
          </li>
        ))}
      </ul>
      <h3>{t.findings.dfm}</h3>
      {findings.length === 0 && <p className="muted">{t.findings.none}</p>}
      <ul className="list">
        {findings.map((f, i) => (
          <li key={i} className={`finding ${f.severity}`}>
            <span className={`badge ${f.severity}`}>{t.status[f.severity] ?? f.severity}</span> {f.message}
            {f.suggestion && (
              <p className="muted small">
                {t.findings.suggestion} {f.suggestion}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
