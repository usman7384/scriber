import type { ReactNode } from "react";
import { apiUrl, type Job } from "../api";
import { seconds } from "../format";
import { useJob } from "../hooks";

interface Props {
  jobId: string;
  onEnd?: (job: Job) => void;
  children?: (job: Job) => ReactNode;
}

export function JobTimeline({ jobId, onEnd, children }: Props) {
  const { steps, job, error } = useJob(jobId, onEnd);
  const status = error ? "failed" : (job?.status ?? "running");
  const progress = steps.at(-1)?.progress;
  return (
    <section className="panel" aria-label="Generation timeline">
      <header className="row">
        <h2>Timeline</h2>
        <span className={`badge ${status}`} role="status">
          {status}
        </span>
      </header>
      {progress !== undefined && (
        <div className="row">
          <progress value={progress} max={100} aria-label="Progress" />
          <span className="muted small">{progress} %</span>
        </div>
      )}
      <ol className="timeline">
        {steps.map((s, i) => (
          <li key={i} className={`step ${s.kind}`}>
            <span className="step-kind">{s.kind}</span>
            {s.attempt > 0 && <span className="muted small">attempt {s.attempt}</span>}
            <span className="muted small push">{seconds(s.elapsed_ms)}</span>
            <p className="step-message">{s.message}</p>
            {s.thumbnail_url && (
              <img src={apiUrl(s.thumbnail_url)} alt={`${s.kind} step preview`} width={96} />
            )}
          </li>
        ))}
      </ol>
      {(error ?? job?.error) && (
        <p role="alert" className="error">
          {error ?? job?.error}
        </p>
      )}
      {job && children?.(job)}
    </section>
  );
}
