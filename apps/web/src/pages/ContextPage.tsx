import { useState } from "react";
import { useParams } from "react-router";
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

export function ContextPage() {
  const projectId = useParams().projectId ?? "";
  const project = useResource(`project:${projectId}`, () => api.project(projectId));
  const context = useResource(`context:${projectId}`, () => api.context(projectId));
  const rules = useResource(`rules:${projectId}`, () => api.rules(projectId));
  const graph = useResource(`graph:${projectId}`, () => api.graph(projectId));
  const [open, setOpen] = useState<string>();
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
            <FileTable files={context.data.files} open={open} onOpen={setOpen} onDelete={remove} />
          ) : (
            <Pending error={context.error} />
          )}
          {openFile && (
            <section className="panel" aria-label={`Facts from ${openFile.name}`}>
              <h2>Facts from {openFile.name}</h2>
              <FactsList projectId={projectId} fileId={openFile.id} />
            </section>
          )}
          <section className="panel">
            <h2>Project rules</h2>
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
