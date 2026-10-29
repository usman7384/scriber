import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { api, exportUrl } from "../api";
import { ModelGallery } from "../components/ModelGallery";
import { Pending } from "../components/Pending";
import { ProjectNav } from "../components/ProjectNav";
import { PromptPanel } from "../components/PromptPanel";
import { JobTimeline } from "../components/Timeline";
import { useResource } from "../hooks";
import { useT } from "../i18n";

export function ProjectPage() {
  const projectId = useParams().projectId ?? "";
  const project = useResource(`project:${projectId}`, () => api.project(projectId));
  const models = useResource(`models:${projectId}`, () => api.models(projectId));
  const active = useResource(`active-jobs:${projectId}`, () => api.activeJobs(projectId));
  const [search, setSearch] = useSearchParams();
  const ids = search.get("context")?.split(",") ?? [];
  const context = useResource(`context:${projectId}:${ids.join()}`, () =>
    ids.length ? api.context(projectId) : Promise.resolve(undefined),
  );
  const [started, setStarted] = useState<string>();
  const t = useT();
  const jobId = started ?? active.data?.[0]?.id;

  if (!project.data) return <Pending error={project.error} />;
  return (
    <section className="stack">
      <ProjectNav project={project.data} />
      <PromptPanel
        projectId={projectId}
        context={context.data?.files.filter((f) => ids.includes(f.id)) ?? []}
        onClearContext={() => setSearch({})}
        onJob={(job) => setStarted(job.id)}
      />
      {jobId && (
        <JobTimeline key={jobId} jobId={jobId} onEnd={models.reload}>
          {(job) =>
            job.status === "done" &&
            job.model_id && (
              <div className="row">
                <Link className="button primary" to={`/m/${job.model_id}`}>
                  {t.timeline.open}
                </Link>
                {job.version && (
                  <a className="button secondary" href={exportUrl(job.model_id, "stl", job.version)} download>
                    {t.timeline.stl}
                  </a>
                )}
              </div>
            )
          }
        </JobTimeline>
      )}
      <h2>{t.project.models}</h2>
      {models.data ? <ModelGallery models={models.data} /> : <Pending error={models.error} />}
    </section>
  );
}
