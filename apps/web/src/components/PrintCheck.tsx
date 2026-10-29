import { useState } from "react";
import { api, type Printability } from "../api";
import { useT } from "../i18n";

export function PrintCheck({ modelId, version }: { modelId: string; version: number }) {
  const t = useT();
  const [report, setReport] = useState<Printability>();
  const [error, setError] = useState<string>();
  const [running, setRunning] = useState(false);
  const check = () => {
    setRunning(true);
    setError(undefined);
    api
      .slice(modelId, version)
      .then(setReport, (e: Error) => setError(e.message))
      .finally(() => setRunning(false));
  };
  const p = t.printability;
  return (
    <div className="stack" aria-label={p.region}>
      <h3>{p.title}</h3>
      <button type="button" className="button secondary" disabled={running} onClick={check}>
        {running ? p.running : p.check}
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {report && (
        <ul className="list">
          <li className="row">
            <span className={`badge ${report.ok ? "done" : "failed"}`}>
              {report.ok ? t.status.pass : t.status.fail}
            </span>
            <span>{p.summary(report.layers, (report.gcode_bytes / 1e6).toFixed(2))}</span>
          </li>
          <li className="row">
            <span>{report.manifold ? p.manifold : p.notManifold}</span>
          </li>
          {report.errors.map((line, i) => (
            <li key={`e${i}`} className="error small">
              {line}
            </li>
          ))}
          {report.warnings.map((line, i) => (
            <li key={`w${i}`} className="muted small">
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
