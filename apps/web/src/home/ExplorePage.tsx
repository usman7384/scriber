import { useState } from "react";
import { useNavigate } from "react-router";
import { api, type Project, type Publication } from "../api";
import { Pending } from "../components/Pending";
import { date } from "../format";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { Popover } from "../ui/Popover";
import { HomeLayout } from "./HomeLayout";
import { PartsGrid } from "./PartsGrid";

export function ExplorePage() {
  const published = useResource("community", api.community);
  const projects = useResource("projects", api.projects);
  const t = useT().community;
  if (!published.data || !projects.data) return <Pending error={published.error ?? projects.error} />;
  const into = projects.data;
  return (
    <HomeLayout projects={into}>
      <h1 className="home-title">{t.title}</h1>
      <p className="home-lead home-lead-sm">{t.lead}</p>
      <PartsGrid
        label={t.region}
        empty={t.none}
        parts={published.data.map((p) => ({
          id: p.id,
          title: p.title,
          created: p.created,
          thumbnail: p.thumbnail_url,
          meta: (
            <p className="part-sub">
              <span>
                <span className="mono">v{p.version}</span> · {t.by(p.author)} · {date(p.created)}
              </span>
            </p>
          ),
          action: <Fork publication={p} projects={into} />,
        }))}
      />
    </HomeLayout>
  );
}

// The fork lands in the project picked here and opens (UI_DIRECTION.md §2, /explore).
function Fork({ publication, projects }: { publication: Publication; projects: Project[] }) {
  const [error, setError] = useState<string>();
  const navigate = useNavigate();
  const t = useT().community;
  const fork = (projectId: string) => {
    setError(undefined);
    api.fork(publication.id, projectId).then(
      (model) => navigate(`/m/${model.id}`),
      (e: Error) => setError(e.message),
    );
  };
  return (
    <Popover
      label={t.into}
      trigger={(props) => (
        <Button {...props} className="part-action" aria-label={t.forkTitle(publication.title)}>
          {t.fork}
        </Button>
      )}
    >
      <span className="eyebrow fork-head">{t.into}</span>
      {projects.length === 0 && <span className="home-empty">{t.noProjects}</span>}
      <ul className="fork-list">
        {projects.map((p) => (
          <li key={p.id}>
            <button type="button" className="home-link" onClick={() => fork(p.id)}>
              {p.name}
            </button>
          </li>
        ))}
      </ul>
      {error && (
        <span role="alert" className="home-error">
          {error}
        </span>
      )}
    </Popover>
  );
}
