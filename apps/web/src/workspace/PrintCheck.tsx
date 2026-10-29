import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { Status } from "../ui/Status";
import type { PrintState } from "./usePrintCheck";

export function PrintCheck({ print }: { print: PrintState }) {
  const t = useT();
  const p = t.printability;
  const { report, error, running, check } = print;
  return (
    <section className="ws-check-group" aria-label={p.region}>
      <div className="ws-section-head">
        <h3 className="eyebrow">{p.title}</h3>
        <Button icon="process" disabled={running} onClick={check}>
          {running ? p.running : p.check}
        </Button>
      </div>
      {error && (
        <p role="alert" className="ws-error">
          {error}
        </p>
      )}
      {report && (
        <ul className="ws-check-list">
          <li>
            <Status state={report.ok ? "pass" : "fail"} />
            <span>{p.summary(report.layers, (report.gcode_bytes / 1e6).toFixed(2))}</span>
          </li>
          <li>
            <Status state={report.manifold ? "pass" : "fail"}>
              {report.manifold ? p.manifold : p.notManifold}
            </Status>
          </li>
          {report.errors.map((line, i) => (
            <li key={`e${i}`} className="ws-error">
              {line}
            </li>
          ))}
          {report.warnings.map((line, i) => (
            <li key={`w${i}`} className="ws-muted">
              {line}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
