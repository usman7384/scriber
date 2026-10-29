import { lazy, Suspense, useState } from "react";
import { useMatch, useNavigate, useParams, useSearchParams } from "react-router";
import { AgentStream } from "../agent/AgentStream";
import { CommandBar } from "../agent/CommandBar";
import { api, type Job, type Model, type Project } from "../api";
import { Pending } from "../components/Pending";
import { byNewest, date } from "../format";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { useShell } from "../shell/context";
import { HomeLayout } from "./HomeLayout";
import { PartsGrid, type Part } from "./PartsGrid";
import { NewProject } from "./ProjectList";

// The sheet and its graph layout load only when Sources opens.
const SourcesSheet = lazy(() => import("../sources/SourcesSheet").then((m) => ({ default: m.SourcesSheet })));

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

  if (!projects.data)
    return (
      <HomeLayout>
        <Pending error={projects.error} />
      </HomeLayout>
    );
  const current = projects.data.find((p) => p.id === projectId);
  if (projectId && !current)
    return (
      <HomeLayout projects={projects.data}>
        <p className="home-empty">{t.notFound}</p>
      </HomeLayout>
    );
  const target = current ?? byNewest(projects.data)[0];
  const title = current?.name ?? (library ? t.home.allParts : t.home.projects);
  const names = Object.fromEntries(projects.data.map((p) => [p.id, p.name]));
  const reload = () => {
    models.reload();
    projects.reload();
  };

  return (
    <HomeLayout projects={projects.data} current={current} allCurrent={library}>
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
        <Suspense>
          <SourcesSheet
            projectId={current.id}
            onClose={() => navigate(`/p/${current.id}`)}
            onUse={(ids) => navigate(`/p/${current.id}?context=${ids.join(",")}`)}
          />
        </Suspense>
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

interface Run {
  id: string;
  resend?: () => Promise<Job>;
}

function Composer({ project, onEnd }: { project: Project; onEnd: () => void }) {
  const active = useResource(`active-jobs:${project.id}`, () => api.activeJobs(project.id));
  const [search] = useSearchParams();
  const contextIds = search.get("context")?.split(",").filter(Boolean) ?? [];
  const [run, setRun] = useState<Run>();
  const { openPalette } = useShell();
  const jobId = run?.id ?? active.data?.[0]?.id;
  const resend = run?.resend;
  return (
    <div className="home-composer">
      <CommandBar
        mode="generate"
        projectId={project.id}
        contextIds={contextIds}
        onJob={(job, again) => setRun({ id: job.id, resend: again })}
        onCommand={openPalette}
      />
      {jobId && (
        <AgentStream
          key={jobId}
          jobId={jobId}
          variant="card"
          onDone={onEnd}
          onRetry={resend && (() => void resend().then((job) => setRun({ id: job.id, resend })))}
        />
      )}
    </div>
  );
}
