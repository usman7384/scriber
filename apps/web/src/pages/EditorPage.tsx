import { useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { api, apiUrl, type FaceDriver, type Job } from "../api";
import { BugDialog } from "../components/BugDialog";
import { ComponentTree } from "../components/ComponentTree";
import { ExportMenu } from "../components/ExportMenu";
import { FaceEdit } from "../components/FaceEdit";
import { Findings } from "../components/Findings";
import { ParamPanel } from "../components/ParamPanel";
import { Pending } from "../components/Pending";
import { PrintCheck } from "../components/PrintCheck";
import { PublishButton } from "../components/PublishButton";
import { RefineBox } from "../components/RefineBox";
import { ShareButton } from "../components/ShareButton";
import { Suggestions } from "../components/Suggestions";
import { JobTimeline } from "../components/Timeline";
import { VersionHistory } from "../components/VersionHistory";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Viewer } from "../viewer/Viewer";

export function EditorPage() {
  const modelId = useParams().modelId ?? "";
  const model = useResource(`model:${modelId}`, () => api.model(modelId));
  const versions = useResource(`versions:${modelId}`, () => api.versions(modelId));
  const [picked, setPicked] = useState<number>();
  const latest = Math.max(0, ...(versions.data ?? []).map((v) => v.number));
  const shown = picked ?? latest;
  const health = useResource("health", () => api.health());
  const tools = health.data?.tools;
  const components = useResource(`components:${modelId}:${shown}`, () =>
    shown ? api.components(modelId, shown) : Promise.resolve([]),
  );
  const [job, setJob] = useState<{ id: string; running: boolean }>();
  const [selected, setSelected] = useState<string>();
  const t = useT();
  const [face, setFace] = useState<FaceDriver>();
  const [error, setError] = useState<string>();
  const main = useRef<HTMLElement>(null);

  if (!model.data || !versions.data) return <Pending error={model.error ?? versions.error} />;
  if (versions.data.length === 0)
    return (
      <section className="stack">
        <h1>{model.data.title}</h1>
        <p className="empty">
          {t.editor.noVersion} <Link to={`/p/${model.data.project_id}`}>{t.editor.backToProject}</Link>
        </p>
      </section>
    );
  const all = versions.data;
  const version = all.find((v) => v.number === shown) ?? all[all.length - 1];
  if (!version) return null;
  const parts = components.data ?? [];
  const nameOf = (id?: string) => parts.find((c) => c.id === id)?.name;

  const fail = (e: Error) => setError(e.message);
  const start = (request: Promise<Job>) => {
    setError(undefined);
    setFace(undefined);
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
          {t.editor.back}
        </Link>
        <h1>{model.data.title}</h1>
        <span className="badge plain">v{version.number}</span>
        {model.data.forked_from && (
          <span className="muted small">
            {t.community.forkedFrom(
              model.data.forked_from.title,
              model.data.forked_from.version,
              model.data.forked_from.author,
            )}
          </span>
        )}
        <span className="push" />
        <Link to={`/p/${model.data.project_id}`} className="button primary">
          {t.editor.newGeneration}
        </Link>
        <ShareButton modelId={modelId} version={version.number} />
        <PublishButton modelId={modelId} version={version.number} />
        <ExportMenu
          modelId={modelId}
          version={version.number}
          freecad={tools?.freecad ?? false}
          onError={fail}
        />
        <BugDialog
          modelId={modelId}
          version={version.number}
          screenshot={() => main.current?.querySelector("canvas")?.toDataURL("image/png")}
        />
      </header>
      <aside className="editor-left panel">
        <h2>{t.editor.components}</h2>
        <ComponentTree components={parts} selected={selected} onSelect={setSelected} />
        <h2>{t.editor.history}</h2>
        <VersionHistory
          versions={all}
          selected={version.number}
          latest={latest}
          onSelect={setPicked}
          onRestore={restore}
        />
      </aside>
      <section className="editor-main" ref={main}>
        {version.status === "failed" && <p className="error">{t.editor.failed}</p>}
        {version.files.glb && (
          <Viewer
            url={apiUrl(version.files.glb)}
            findings={version.findings}
            selected={nameOf(selected)}
            onSelect={(name) => setSelected(parts.find((c) => c.name === name)?.id)}
            onPickFace={(hit) =>
              api.faceDriver(modelId, { ...hit, version: version.number }).then(setFace, (e: Error) => {
                setFace(undefined);
                fail(e);
              })
            }
          />
        )}
        {face && (
          <FaceEdit
            key={`${face.part}.${face.feature}.${face.param}`}
            driver={face}
            params={version.params}
            busy={busy}
            onApply={(values) => start(api.setParams(modelId, values))}
            onClose={() => setFace(undefined)}
          />
        )}
        <RefineBox
          target={nameOf(selected)}
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
        <h2>{t.editor.parameters}</h2>
        <ParamPanel
          params={version.params}
          busy={busy}
          onApply={(values) => start(api.setParams(modelId, values))}
        />
        {version.metrics && (
          <p className="muted small">
            {t.editor.volume} {(version.metrics.volume / 1000).toFixed(2)} cm³
            {version.metrics.mass_g != null && ` · ${t.editor.mass} ${version.metrics.mass_g.toFixed(1)} g`}
          </p>
        )}
        <Findings checks={version.checks} findings={version.findings} />
        {tools?.prusaslicer && version.files.stl && (
          <PrintCheck key={version.number} modelId={modelId} version={version.number} />
        )}
        <Suggestions
          modelId={modelId}
          version={version.number}
          params={version.params}
          busy={busy}
          onAccept={start}
        />
      </aside>
    </div>
  );
}
