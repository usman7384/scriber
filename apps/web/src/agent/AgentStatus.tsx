import type { Job, Version } from "../api";
import { useLang, useT } from "../i18n";
import { Button } from "../ui/Button";
import { Icon } from "../ui/icons";
import { versionBefore } from "./diff";
import { ago, byAgent } from "./steps";
import "./agent.css";

interface Props {
  job?: Job | undefined;
  versions: Version[];
  // The version to restore as a new one.
  onRevert: (n: number) => void;
}

export function AgentStatus({ job, versions, onRevert }: Props) {
  const t = useT();
  const [lang] = useLang();
  const a = t.agent.activity;
  const latest = versions.at(-1);
  const running = job && (job.status === "queued" || job.status === "running");
  const step = job?.steps.at(-1);
  const checks = latest?.checks ?? [];
  const passed = checks.filter((c) => c.passed).length;
  const sentence = running
    ? step
      ? a.running(t.agent.stream.kinds[step.kind] ?? step.kind)
      : t.agent.stream.working
    : job?.status === "failed"
      ? a.failed(job.error ?? t.agent.stream.failed)
      : latest
        ? [
            a.latest(latest.number, t.origin[latest.origin] ?? latest.origin, ago(latest.created, lang)),
            checks.length > 0 && a.checks(passed, checks.length),
          ]
            .filter(Boolean)
            .join(" · ")
        : a.idle;
  const previous = latest && byAgent(latest) && !running ? versionBefore(versions, latest.number) : undefined;
  return (
    <div className="agent-status">
      <Icon name="agent" className="agent-accent" />
      <span role="status" aria-live="polite" className="agent-status-text">
        {sentence}
      </span>
      {latest && previous && (
        <Button
          variant="ghost"
          icon="undo"
          aria-label={a.revertLabel(latest.number, previous.number)}
          onClick={() => onRevert(previous.number)}
        >
          {a.revert}
        </Button>
      )}
    </div>
  );
}
