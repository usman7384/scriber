import { useState } from "react";
import { AgentStatus } from "../../src/agent/AgentStatus";
import { AgentStream } from "../../src/agent/AgentStream";
import type { Target } from "../../src/agent/BarParts";
import { CommandBar } from "../../src/agent/CommandBar";
import { Proposals } from "../../src/agent/Proposals";
import { VersionScrubber } from "../../src/agent/VersionScrubber";
import { api, apiUrl, type Job } from "../../src/api";
import { useResource } from "../../src/hooks";
import "./harness.css";

const query = new URLSearchParams(location.search);

interface Run {
  id: string;
  resend?: () => Promise<Job>;
}

export function Home() {
  const [run, setRun] = useState<Run>();
  const retry = (resend: () => Promise<Job>) => resend().then((job) => setRun({ id: job.id, resend }));
  return (
    <main className="h-home">
      <CommandBar
        mode="generate"
        projectId="p1"
        contextIds={query.get("context")?.split(",") ?? []}
        onJob={(job, resend) => setRun({ id: job.id, resend })}
      />
      {run && (
        <AgentStream
          key={run.id}
          jobId={run.id}
          variant="card"
          onRetry={run.resend && (() => void retry(run.resend as () => Promise<Job>))}
        />
      )}
    </main>
  );
}

const plate: Target = { id: "plate", label: "Sensor mounting plate", kind: "part" };

export function Workspace() {
  const versions = useResource("versions", () => api.versions("m1"));
  const [shown, setShown] = useState<number>();
  const [run, setRun] = useState<Run | undefined>(() => {
    const id = query.get("job");
    return id ? { id } : undefined;
  });
  const [ended, setEnded] = useState<Job>();
  const [target, setTarget] = useState(query.has("target") ? plate : undefined);
  const all = versions.data ?? [];
  const latest = all.at(-1)?.number ?? 0;
  const version = all.find((v) => v.number === (shown ?? latest));
  const done = (job: Job) => {
    setEnded(job);
    setRun(undefined);
    versions.reload();
    if (job.version) setShown(job.version);
  };
  const restore = (n: number) =>
    api.restore("m1", n).then((v) => {
      versions.reload();
      setShown(v.number);
    });
  return (
    <main className="h-ws">
      {version?.thumbnail_url && <img className="h-part" src={apiUrl(version.thumbnail_url)} alt="" />}
      <div className="h-left">
        {run ? (
          <AgentStream key={run.id} jobId={run.id} variant="dock" onDone={done} />
        ) : (
          <AgentStatus job={ended} versions={all} onRevert={(n) => void restore(n)} />
        )}
      </div>
      <aside className="h-insp">
        <Proposals key={latest} modelId="m1" onApplied={(job) => setRun({ id: job.id })} />
      </aside>
      <div className="h-cmd">
        <CommandBar
          mode="refine"
          modelId="m1"
          target={target}
          onClearTarget={() => setTarget(undefined)}
          busy={run !== undefined}
          onJob={(job) => setRun({ id: job.id })}
        />
      </div>
      <div className="h-scrub">
        {all.length > 0 && (
          <VersionScrubber
            versions={all}
            shown={shown ?? latest}
            onShow={setShown}
            onRestore={(n) => void restore(n)}
            onCompare={() => undefined}
          />
        )}
      </div>
    </main>
  );
}
