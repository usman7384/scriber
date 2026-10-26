import { useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api";
import { ModelGallery } from "../components/ModelGallery";
import { Pending } from "../components/Pending";
import { ProjectNav } from "../components/ProjectNav";
import { PromptPanel } from "../components/PromptPanel";
import { JobTimeline } from "../components/Timeline";
import { useResource } from "../hooks";

export function ProjectPage() {
  const projectId = useParams().projectId ?? "";
  const project = useResource(`project:${projectId}`, () => api.project(projectId));
  const models = useResource(`models:${projectId}`, () => api.models(projectId));
  const active = useResource(`active-jobs:${projectId}`, () => api.activeJobs(projectId));
  const [started, setStarted] = useState<string>();
  const jobId = started ?? active.data?.[0]?.id;

  if (!project.data) return <Pending error={project.error} />;
  return (
    <section className="stack">
      <ProjectNav project={project.data} />
      <PromptPanel projectId={projectId} onJob={(job) => setStarted(job.id)} />
      {jobId && (
        <JobTimeline key={jobId} jobId={jobId} onEnd={models.reload}>
          {(job) =>
            job.status === "done" &&
            job.model_id && (
              <Link className="button primary" to={`/m/${job.model_id}`}>
                Open model
              </Link>
            )
          }
        </JobTimeline>
      )}
      <h2>Models</h2>
      {models.data ? <ModelGallery models={models.data} /> : <Pending error={models.error} />}
    </section>
  );
}
