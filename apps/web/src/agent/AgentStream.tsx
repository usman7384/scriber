import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api, apiUrl, exportUrl, type Job } from "../api";
import { seconds } from "../format";
import { useJob, useResource } from "../hooks";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { Icon, type IconName } from "../ui/icons";
import { changeText, paramDiff, versionBefore } from "./diff";
import { stepStates, type StepState } from "./steps";
import "./agent.css";

interface Props {
  jobId: string;
  variant: "card" | "dock";
  // Called when the job ends, done or failed.
  onDone?: (job: Job) => void;
  onRetry?: () => void;
}

const glyph: Record<StepState, IconName> = { pass: "pass", fail: "fail", run: "clock" };

function useChanges(job?: Job) {
  const model = job?.status === "done" ? job.model_id : undefined;
  const n = job?.version ?? 0;
  const versions = useResource(`agent-changes:${model}:${n}`, () =>
    model ? api.versions(model) : Promise.resolve([]),
  );
  const shown = versions.data?.find((v) => v.number === n);
  const before = versionBefore(versions.data ?? [], n);
  return shown && { count: shown.params.length, diff: before && paramDiff(before.params, shown.params) };
}

export function AgentStream({ jobId, variant, onDone, onRetry }: Props) {
  const t = useT();
  const s = t.agent.stream;
  const { steps, job, error } = useJob(jobId, onDone);
  const end = error ? "failed" : job?.status === "done" || job?.status === "failed" ? job.status : undefined;
  const states = stepStates(steps, end);
  const last = steps.at(-1);
  const [open, setOpen] = useState<boolean>();
  const expanded = open ?? !(variant === "dock" && end);
  const changes = useChanges(job);
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (list.current && !reduce) list.current.scrollTop = list.current.scrollHeight;
  }, [steps.length]);

  const title =
    end === "done" && job?.version
      ? s.done(job.version)
      : end
        ? s.failed
        : last
          ? `${s.working} · ${s.kinds[last.kind] ?? last.kind}`
          : s.working;
  const failure = error ?? job?.error;

  return (
    <section className="agent-stream" data-variant={variant} aria-label={t.timeline.region}>
      <header className="agent-stream-head">
        <Icon name="agent" className="agent-accent" />
        <b className="agent-stream-title">{title}</b>
        {last && <span className="agent-meta mono">{seconds(last.elapsed_ms)}</span>}
        <span className="agent-spacer" />
        <span role="status" className="agent-badge mono" data-status={end ?? "running"}>
          {t.status[end ?? "running"]}
        </span>
        <IconButton
          icon={expanded ? "chevronDown" : "chevronUp"}
          label={expanded ? s.collapse : s.expand}
          aria-expanded={expanded}
          onClick={() => setOpen(!expanded)}
        />
      </header>
      {last?.progress !== undefined && (
        <progress
          className="agent-hairline"
          value={last.progress}
          max={100}
          aria-label={t.timeline.progress}
        />
      )}
      <ol ref={list} className="agent-steps" hidden={!expanded}>
        {steps.map((step, i) => {
          const state = states[i] ?? "pass";
          const head = (
            <>
              <Icon name={glyph[state]} size={14} className="agent-step-glyph" />
              <span className="step-kind">{s.kinds[step.kind] ?? step.kind}</span>
              {step.attempt > 0 && <span className="agent-meta">{t.timeline.attempt(step.attempt)}</span>}
              <span className="agent-meta mono agent-push">{seconds(step.elapsed_ms)}</span>
            </>
          );
          const repairs = step.kind === "repair" && steps[i - 1]?.kind === "check";
          return (
            <li key={i} className="agent-step" data-state={state} data-kind={step.kind}>
              {step.kind === "check" || step.kind === "repair" ? (
                <details open>
                  <summary className="agent-step-head">{head}</summary>
                  {repairs && <p className="agent-linked">{s.repairs}</p>}
                  <p className="agent-step-detail mono">{step.message}</p>
                </details>
              ) : (
                <>
                  <div className="agent-step-head">{head}</div>
                  <p className="agent-step-message">{step.message}</p>
                </>
              )}
              {step.thumbnail_url && (
                <img
                  className="agent-step-thumb"
                  src={apiUrl(step.thumbnail_url)}
                  alt={t.timeline.preview(step.kind)}
                  width={64}
                  height={64}
                />
              )}
            </li>
          );
        })}
      </ol>
      {changes && expanded && (
        <div className="agent-step-detail mono agent-changes">
          {changes.diff
            ? changes.diff.map((c) => <div key={c.name}>~ {changeText(c)}</div>)
            : s.params(changes.count)}
        </div>
      )}
      {failure && (
        <p role="alert" className="agent-error">
          {failure}
        </p>
      )}
      {end === "failed" && onRetry && (
        <div className="agent-bar-row">
          <Button icon="undo" onClick={onRetry}>
            {s.retry}
          </Button>
        </div>
      )}
      {variant === "card" && end === "done" && job?.model_id && (
        <div className="agent-bar-row">
          <Link className="ui-button" data-variant="primary" to={`/m/${job.model_id}`}>
            {t.timeline.open}
          </Link>
          {job.version && (
            <a className="ui-button" href={exportUrl(job.model_id, "stl", job.version)} download>
              <Icon name="deliver" />
              {t.timeline.stl}
            </a>
          )}
        </div>
      )}
    </section>
  );
}
