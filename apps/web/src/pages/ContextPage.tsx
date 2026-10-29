import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { api } from "../api";
import { Pending } from "../components/Pending";
import { ProjectNav } from "../components/ProjectNav";
import { FactsList } from "../context/FactsList";
import { FileTable } from "../context/FileTable";
import { GraphPanel } from "../context/GraphPanel";
import { KbStatsCard } from "../context/KbStatsCard";
import { RulesTable } from "../context/RulesTable";
import { UploadZone } from "../context/UploadZone";
import { useResource } from "../hooks";
import { useT } from "../i18n";

export function ContextPage() {
  const projectId = useParams().projectId ?? "";
  const project = useResource(`project:${projectId}`, () => api.project(projectId));
  const context = useResource(`context:${projectId}`, () => api.context(projectId));
  const rules = useResource(`rules:${projectId}`, () => api.rules(projectId));
  const graph = useResource(`graph:${projectId}`, () => api.graph(projectId));
  const models = useResource(`models:${projectId}`, () => api.models(projectId));
  const [open, setOpen] = useState<string>();
  const [chosen, setChosen] = useState<string[]>([]);
  const navigate = useNavigate();
  const t = useT().context;
  const [error, setError] = useState<string>();

  const refresh = () => {
    context.reload();
    rules.reload();
    graph.reload();
  };
  const remove = (fileId: string) =>
    api.deleteFile(projectId, fileId).then(refresh, (e: Error) => setError(e.message));
  const openFile = context.data?.files.find((f) => f.id === open);

  if (!project.data) return <Pending error={project.error} />;
  return (
    <section className="stack">
      <ProjectNav project={project.data} />
      <div className="context-grid">
        <div className="stack">
          <UploadZone projectId={projectId} onChange={refresh} />
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          {context.data ? (
            <FileTable
              files={context.data.files}
              open={open}
              chosen={chosen}
              titles={Object.fromEntries((models.data ?? []).map((m) => [m.id, m.title]))}
              onOpen={setOpen}
              onChoose={setChosen}
              onDelete={remove}
            />
          ) : (
            <Pending error={context.error} />
          )}
          <button
            type="button"
            className="primary"
            disabled={chosen.length === 0}
            onClick={() => navigate(`/p/${projectId}?context=${chosen.join(",")}`)}
          >
            {t.useSelected(chosen.length)}
          </button>
          {openFile && (
            <section className="panel" aria-label={t.factsFrom(openFile.name)}>
              <h2>{t.factsFrom(openFile.name)}</h2>
              <FactsList projectId={projectId} fileId={openFile.id} />
            </section>
          )}
          <section className="panel">
            <h2>{t.rules}</h2>
            {rules.data ? <RulesTable rules={rules.data} /> : <Pending error={rules.error} />}
          </section>
        </div>
        <div className="stack">
          {context.data && <KbStatsCard stats={context.data.stats} />}
          {graph.data ? <GraphPanel graph={graph.data} /> : <Pending error={graph.error} />}
        </div>
      </div>
    </section>
  );
}
