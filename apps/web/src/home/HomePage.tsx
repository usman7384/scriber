import { useState } from "react";
import { Link, useMatch, useNavigate, useParams, useSearchParams } from "react-router";
import { api, exportUrl, type Model, type Project } from "../api";
import { Pending } from "../components/Pending";
import { PromptPanel } from "../components/PromptPanel";
import { JobTimeline } from "../components/Timeline";
import { byNewest, date } from "../format";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { SourcesSheet } from "../sources/SourcesSheet";
import { HomeLayout } from "./HomeLayout";
import { PartsGrid, type Part } from "./PartsGrid";
import { NewProject } from "./ProjectList";

const allModels = async () => (await Promise.all((await api.projects()).map((p) => api.models(p.id)))).flat();

// One screen for /, /library, /p/:id and /p/:id/context (docs/design/UI_DIRECTION.md §2).
export function HomePage() {
  const projectId = useParams().projectId;
  const sources = useMatch("/p/:projectId/context") !== null;
  const library = useMatch("/library") !== null;
  const projects = useResource("projects", api.projects);
  const models = useResource(`parts:${projectId ?? ""}`, () =>
    projectId ? api.models(projectId) : allModels(),
  );
  const navigate = useNavigate();
  const t = useT();

  if (!projects.data) return <Pending error={projects.error} />;
  const current = projects.data.find((p) => p.id === projectId);
  if (projectId && !current) return <p className="home-empty">{t.notFound}</p>;
  const target = current ?? byNewest(projects.data)[0];
  const title = current?.name ?? (library ? t.home.allParts : t.home.projects);
  const names = Object.fromEntries(projects.data.map((p) => [p.id, p.name]));
  const reload = () => {
    models.reload();
    projects.reload();
  };

  return (
    <HomeLayout projects={projects.data} current={current} allCurrent={!projectId}>
      <div className="eyebrow home-eyebrow">
        <h1>{title}</h1>
        {target && <span>· {current ? t.home.newPart : t.home.newPartIn(target.name)}</span>}
      </div>
      <p className="home-lead">{target ? t.home.lead : t.projects.none}</p>
      {target ? <Composer key={target.id} project={target} onEnd={reload} /> : <NewProject startOpen />}
      {models.data ? (
        <PartsGrid
          label={t.gallery.region}
          parts={models.data.map((m) => modelPart(m, current ? undefined : names[m.project_id]))}
          empty={t.gallery.none}
        />
      ) : (
        <Pending error={models.error} />
      )}
      {sources && current && (
        <SourcesSheet
          projectId={current.id}
          onClose={() => navigate(`/p/${current.id}`)}
          onUse={(ids) => navigate(`/p/${current.id}?context=${ids.join(",")}`)}
        />
      )}
    </HomeLayout>
  );
}

function ModelMeta({ model, project }: { model: Model; project: string | undefined }) {
  const t = useT();
  return (
    <>
      <p className="part-sub">
        <span>
          {project && `${project} · `}
          <span className="mono">
            {model.latest_version === null ? t.gallery.noVersion : `v${model.latest_version}`}
          </span>
        </span>
        <span>{date(model.created)}</span>
      </p>
      {model.forked_from && (
        <p className="part-sub">
          {t.community.forkedFrom(
            model.forked_from.title,
            model.forked_from.version,
            model.forked_from.author,
          )}
        </p>
      )}
    </>
  );
}

const modelPart = (m: Model, project: string | undefined): Part => ({
  id: m.id,
  title: m.title,
  created: m.created,
  thumbnail: m.thumbnail_url,
  href: `/m/${m.id}`,
  meta: <ModelMeta model={m} project={project} />,
});

// C's command bar and agent stream replace PromptPanel and JobTimeline in this slot.
function Composer({ project, onEnd }: { project: Project; onEnd: () => void }) {
  const active = useResource(`active-jobs:${project.id}`, () => api.activeJobs(project.id));
  const [search, setSearch] = useSearchParams();
  const ids = search.get("context")?.split(",") ?? [];
  const context = useResource(`context:${project.id}:${ids.join()}`, () =>
    ids.length ? api.context(project.id) : Promise.resolve(undefined),
  );
  const [started, setStarted] = useState<string>();
  const t = useT();
  const jobId = started ?? active.data?.[0]?.id;
  return (
    <div className="home-composer">
      <PromptPanel
        projectId={project.id}
        context={context.data?.files.filter((f) => ids.includes(f.id)) ?? []}
        onClearContext={() => setSearch({})}
        onJob={(job) => setStarted(job.id)}
      />
      {jobId && (
        <JobTimeline key={jobId} jobId={jobId} onEnd={onEnd}>
          {(job) =>
            job.status === "done" &&
            job.model_id && (
              <div className="home-done">
                <Link className="ui-button" data-variant="primary" to={`/m/${job.model_id}`}>
                  {t.timeline.open}
                </Link>
                {job.version && (
                  <a className="ui-button" href={exportUrl(job.model_id, "stl", job.version)} download>
                    {t.timeline.stl}
                  </a>
                )}
              </div>
            )
          }
        </JobTimeline>
      )}
    </div>
  );
}
