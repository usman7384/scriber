import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, apiUrl, exportUrl, type ExportFormat, type Finding, type Job } from "../api";
import { BugDialog } from "../components/BugDialog";
import { Pending } from "../components/Pending";
import { RefineBox } from "../components/RefineBox";
import { Suggestions } from "../components/Suggestions";
import { JobTimeline } from "../components/Timeline";
import { VersionHistory } from "../components/VersionHistory";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Viewer } from "../viewer/Viewer";
import { ChecksPopover } from "../workspace/ChecksPopover";
import { DeliverMenu } from "../workspace/DeliverMenu";
import { Inspector, type Selection } from "../workspace/inspector/Inspector";
import { usePrintCheck } from "../workspace/usePrintCheck";
import { ShareButton } from "../workspace/ShareButton";
import { useShortcuts } from "../workspace/shortcuts";
import { StructureRail } from "../workspace/StructureRail";
import { tally } from "../workspace/tally";
import { Workspace } from "../workspace/Workspace";

const focusParam = (name: string) =>
  requestAnimationFrame(() => document.getElementById(`param-${name}`)?.focus());

export function EditorPage() {
  const modelId = useParams().modelId ?? "";
  const navigate = useNavigate();
  const model = useResource(`model:${modelId}`, () => api.model(modelId));
  const versions = useResource(`versions:${modelId}`, () => api.versions(modelId));
  const projectId = model.data?.project_id;
  const project = useResource(`project:${projectId ?? ""}`, () =>
    projectId ? api.project(projectId) : Promise.resolve(undefined),
  );
  const [picked, setPicked] = useState<number>();
  const latest = Math.max(0, ...(versions.data ?? []).map((v) => v.number));
  const shown = picked ?? latest;
  const health = useResource("health", () => api.health());
  const tools = health.data?.tools;
  const components = useResource(`components:${modelId}:${shown}`, () =>
    shown ? api.components(modelId, shown) : Promise.resolve([]),
  );
  const [job, setJob] = useState<{ id: string; running: boolean }>();
  const [selection, setSelection] = useState<Selection>();
  const [hidden, setHidden] = useState<string[]>([]);
  const [error, setError] = useState<string>();
  const pill = useRef<HTMLButtonElement>(null);
  const print = usePrintCheck(modelId, shown);
  const t = useT();
  // Esc closes an open popover, menu or dialog first (the browser does that); only then does it clear the selection.
  useShortcuts({
    Escape: () =>
      !document.querySelector(":popover-open, details[open], dialog[open]") && setSelection(undefined),
  });

  if (!model.data || !versions.data) return <Pending error={model.error ?? versions.error} />;
  if (versions.data.length === 0)
    return (
      <section className="ws-blank">
        <h1>{model.data.title}</h1>
        <p>
          {t.editor.noVersion} <Link to={`/p/${model.data.project_id}`}>{t.editor.backToProject}</Link>
        </p>
      </section>
    );
  const all = versions.data;
  const version = all.find((v) => v.number === shown) ?? all[all.length - 1];
  if (!version) return null;
  const newest = all.find((v) => v.number === latest);
  const parts = components.data ?? [];
  const nameOf = (id?: string | null) => parts.find((c) => c.id === id)?.name;
  const selectedPart =
    selection?.kind === "part"
      ? selection.id
      : selection?.kind === "face"
        ? selection.driver.part
        : selection?.kind === "finding"
          ? version.findings[selection.index]?.part
          : undefined;
  const target = parts.find((c) => c.id === selectedPart)?.id;
  const sourcesHref = `/p/${model.data.project_id}/context`;

  const fail = (e: Error) => setError(e.message);
  const start = (request: Promise<Job>) => {
    setError(undefined);
    setSelection((s) => (s?.kind === "face" ? undefined : s));
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
  const setParams = (values: Record<string, number>) => start(api.setParams(modelId, values));
  const ask = (f: Finding) =>
    start(
      api.refine(modelId, {
        instruction: t.findings.fixRequest(f.message, f.suggestion ?? ""),
        ...(f.part && { target: f.part }),
      }),
    );
  // A plain download link cannot show why the API refused, so the FreeCAD file is fetched first.
  const downloadFcstd = () =>
    api.exportFile(modelId, "fcstd", version.number).then(({ blob, name }) => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name;
      link.click();
      URL.revokeObjectURL(link.href);
    }, fail);
  const formats: [string, ExportFormat][] = [
    ["STEP", "step"],
    ["STL", "stl"],
    ["GLB", "glb"],
    [t.deliver.script, "py"],
    [t.deliver.ir, "ir"],
  ];
  const n = tally(version);
  const slicer = tools?.prusaslicer && version.files.stl ? print : undefined;
  const face = selection?.kind === "face" ? selection : undefined;
  const driven = face && version.params.find((p) => p.name === face.driver.param);
  const firstAssumed = version.params.find((p) => p.provenance.source === "default");

  return (
    <Workspace
      title={model.data.title}
      version={version.number}
      project={project.data && { href: `/p/${project.data.id}`, name: project.data.name }}
      badges={
        <>
          <ChecksPopover
            version={version}
            print={slicer}
            pill={pill}
            onFinding={(index) => {
              setSelection({ kind: "finding", index });
              requestAnimationFrame(() =>
                document.querySelector<HTMLElement>(`[data-finding="${index}"]`)?.focus(),
              );
            }}
            onParam={(name) => {
              setSelection(undefined);
              focusParam(name);
            }}
          />
          {model.data.forked_from && (
            <span className="ws-muted ws-wide">
              {t.community.forkedFrom(
                model.data.forked_from.title,
                model.data.forked_from.version,
                model.data.forked_from.author,
              )}
            </span>
          )}
        </>
      }
      actions={
        <>
          <span className="ws-desktop">
            <BugDialog
              modelId={modelId}
              version={version.number}
              screenshot={() =>
                document.querySelector<HTMLCanvasElement>(".viewer canvas")?.toDataURL("image/png")
              }
            />
          </span>
          <ShareButton modelId={modelId} version={version.number} />
          <DeliverMenu
            heading={t.deliver.export}
            links={formats.map(([label, fmt]) => [label, exportUrl(modelId, fmt, version.number)])}
            fcstd={{ available: tools?.freecad ?? false, download: () => void downloadFcstd() }}
            publish={() => api.publish(modelId, version.number)}
            checkPrint={
              slicer &&
              (() => {
                slicer.check();
                pill.current?.click();
              })
            }
          />
        </>
      }
      viewport={
        <>
          {version.files.glb && (
            <Viewer
              url={apiUrl(version.files.glb)}
              findings={version.findings}
              selected={nameOf(target)}
              hidden={hidden.flatMap((id) => nameOf(id) ?? [])}
              finding={selection?.kind === "finding" ? selection.index : undefined}
              driving={
                face &&
                driven && {
                  at: face.hit.point,
                  normal: face.hit.normal,
                  value: driven.value,
                  unit: driven.unit,
                  label: t.viewer.driving(driven.label),
                  busy,
                  onCommit: (value) => setParams({ [driven.name]: value }),
                }
              }
              pinActions={{
                onSelect: (index) => setSelection({ kind: "finding", index }),
                onAsk: ask,
                onShowRule: () => void navigate(sourcesHref),
              }}
              onSelect={(name) => {
                const id = parts.find((c) => c.name === name)?.id;
                setSelection(id ? { kind: "part", id } : undefined);
              }}
              onPickFace={(hit) =>
                api.faceDriver(modelId, { ...hit, version: version.number }).then(
                  (driver) => setSelection({ kind: "face", driver, hit }),
                  (e: Error) => {
                    setSelection(undefined);
                    fail(e);
                  },
                )
              }
            />
          )}
          {version.status === "failed" && <p className="ws-banner ws-error">{t.editor.failed}</p>}
        </>
      }
      rail={
        <StructureRail
          components={parts}
          selected={target}
          face={face && { part: face.driver.part, param: driven?.label ?? face.driver.param }}
          hidden={hidden}
          counts={{
            files: project.data?.file_count,
            checks: `${n.pass} / ${version.checks.length + version.findings.length}`,
            assumed: n.assumed,
          }}
          sourcesHref={sourcesHref}
          onSelect={(id) => setSelection(id ? { kind: "part", id } : undefined)}
          onHidden={setHidden}
          onChecks={() => pill.current?.click()}
          onAssumptions={() => {
            setSelection(undefined);
            if (firstAssumed) focusParam(firstAssumed.name);
          }}
          onProposals={() => document.getElementById("ws-proposals")?.scrollIntoView({ block: "nearest" })}
        />
      }
      inspector={
        <Inspector
          title={model.data.title}
          version={version}
          latest={newest}
          components={parts}
          selection={selection}
          busy={busy}
          sourcesHref={sourcesHref}
          onApply={setParams}
          onClearSelection={() => setSelection(undefined)}
          onAsk={ask}
          onBack={() => setPicked(latest)}
          proposals={
            <section id="ws-proposals" className="ws-insp-section">
              <Suggestions
                modelId={modelId}
                version={version.number}
                params={version.params}
                busy={busy}
                onAccept={start}
              />
            </section>
          }
        />
      }
      stream={
        (error || job) && (
          <>
            {error && (
              <p role="alert" className="ws-error ws-float">
                {error}
              </p>
            )}
            {job && <JobTimeline key={job.id} jobId={job.id} onEnd={ended} />}
          </>
        )
      }
      command={
        <RefineBox
          target={nameOf(target)}
          busy={busy}
          onClearTarget={() => setSelection(undefined)}
          onRefine={(instruction) => start(api.refine(modelId, { instruction, ...(target && { target }) }))}
        />
      }
      versions={
        <VersionHistory
          versions={all}
          selected={version.number}
          latest={latest}
          onSelect={setPicked}
          onRestore={restore}
        />
      }
    />
  );
}
