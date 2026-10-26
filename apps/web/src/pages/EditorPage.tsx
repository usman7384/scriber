import { useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { api, apiUrl, type Job } from "../api";
import { BugDialog } from "../components/BugDialog";
import { ComponentTree } from "../components/ComponentTree";
import { ExportMenu } from "../components/ExportMenu";
import { Findings } from "../components/Findings";
import { ParamPanel } from "../components/ParamPanel";
import { Pending } from "../components/Pending";
import { RefineBox } from "../components/RefineBox";
import { ShareButton } from "../components/ShareButton";
import { JobTimeline } from "../components/Timeline";
import { VersionHistory } from "../components/VersionHistory";
import { useResource } from "../hooks";
import { Viewer } from "../viewer/Viewer";

export function EditorPage() {
  const modelId = useParams().modelId ?? "";
  const model = useResource(`model:${modelId}`, () => api.model(modelId));
  const versions = useResource(`versions:${modelId}`, () => api.versions(modelId));
  const [picked, setPicked] = useState<number>();
  const [job, setJob] = useState<{ id: string; running: boolean }>();
  const [parts, setParts] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>();
  const [error, setError] = useState<string>();
  const main = useRef<HTMLElement>(null);

  if (!model.data || !versions.data) return <Pending error={model.error ?? versions.error} />;
  if (versions.data.length === 0)
    return (
      <section className="stack">
        <h1>{model.data.title}</h1>
        <p className="empty">
          This model has no version yet: its generation is still running or was interrupted.{" "}
          <Link to={`/p/${model.data.project_id}`}>Back to the project</Link>
        </p>
      </section>
    );
  const all = versions.data;
  const latest = Math.max(...all.map((v) => v.number));
  const version = all.find((v) => v.number === (picked ?? latest)) ?? all[all.length - 1];
  if (!version) return null;

  const fail = (e: Error) => setError(e.message);
  const start = (request: Promise<Job>) => {
    setError(undefined);
    request.then((j) => setJob({ id: j.id, running: true }), fail);
  };
  const ended = (j: Job) => {
    setJob({ id: j.id, running: false });
    versions.reload();
    model.reload();
    if (j.status === "done" && j.version) setPicked(j.version);
  };
  const restore = (n: number) =>
    api.restore(modelId, n).then((v) => {
      versions.reload();
      setPicked(v.number);
    }, fail);
  const busy = job?.running ?? false;

  return (
    <div className="editor">
      <header className="editor-head">
        <Link to={`/p/${model.data.project_id}`} className="button ghost">
          ← Project
        </Link>
        <h1>{model.data.title}</h1>
        <span className="badge plain">v{version.number}</span>
        <span className="push" />
        <ShareButton modelId={modelId} version={version.number} />
        <ExportMenu modelId={modelId} version={version.number} />
        <BugDialog
          modelId={modelId}
          version={version.number}
          screenshot={() => main.current?.querySelector("canvas")?.toDataURL("image/png")}
        />
      </header>
      <aside className="editor-left panel">
        <h2>Components</h2>
        <ComponentTree parts={parts} selected={selected} onSelect={setSelected} />
        <h2>History</h2>
        <VersionHistory
          versions={all}
          selected={version.number}
          latest={latest}
          onSelect={setPicked}
          onRestore={restore}
        />
      </aside>
      <section className="editor-main" ref={main}>
        {version.status === "failed" && (
          <p className="error">This version failed to build; its checks and history show why.</p>
        )}
        {version.files.glb && (
          <Viewer
            url={apiUrl(version.files.glb)}
            findings={version.findings}
            selected={selected}
            onSelect={setSelected}
            onLoad={(info) => setParts(info.parts)}
          />
        )}
        <RefineBox
          target={selected}
          busy={busy}
          onClearTarget={() => setSelected(undefined)}
          onRefine={(instruction) =>
            start(api.refine(modelId, { instruction, ...(selected && { target: selected }) }))
          }
        />
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {job && <JobTimeline key={job.id} jobId={job.id} onEnd={ended} />}
      </section>
      <aside className="editor-right panel">
        <h2>Parameters</h2>
        <ParamPanel
          params={version.params}
          busy={busy}
          onApply={(values) => start(api.setParams(modelId, values))}
        />
        {version.metrics && (
          <p className="muted small">
            Volume {(version.metrics.volume / 1000).toFixed(2)} cm³
            {version.metrics.mass_g != null && ` · Mass ${version.metrics.mass_g.toFixed(1)} g`}
          </p>
        )}
        <Findings checks={version.checks} findings={version.findings} />
      </aside>
    </div>
  );
}
