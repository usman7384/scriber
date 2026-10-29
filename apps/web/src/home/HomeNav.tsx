import { Link, NavLink, useNavigate } from "react-router";
import type { Project } from "../api";
import { useLang, useT } from "../i18n";
import { Icon } from "../ui/icons";
import { NewProject, ProjectList } from "./ProjectList";

interface Props {
  projects: Project[];
  current?: Project | undefined;
  allCurrent?: boolean;
}

export function HomeNav({ projects, current, allCurrent = false }: Props) {
  const t = useT();
  const [lang] = useLang();
  const navigate = useNavigate();
  return (
    <nav className="home-nav" aria-label={t.nav.main}>
      <Link to="/" className="home-brand">
        <Icon name="mark" />
        <span className="home-link-text">Partwright</span>
      </Link>
      <select
        className="home-switcher"
        aria-label={t.home.switcher}
        value={current?.id ?? ""}
        onChange={(e) => navigate(e.target.value ? `/p/${e.target.value}` : "/library")}
      >
        <option value="">{t.home.allParts}</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <span className="eyebrow home-group">{t.home.projects}</span>
      <ProjectList projects={projects} allCurrent={allCurrent} />
      <NewProject />
      {current && (
        <nav className="home-project" aria-label={t.project.tabs}>
          <span className="eyebrow home-group">{current.name}</span>
          <NavLink to={`/p/${current.id}/context`} className="home-link">
            <Icon name="document" />
            <span className="home-link-text">{t.context.title}</span>
            <span className="home-count" aria-hidden>
              {current.file_count}
            </span>
          </NavLink>
        </nav>
      )}
      <span className="home-spacer" />
      <NavLink to="/explore" className="home-link">
        <Icon name="globe" />
        <span className="home-link-text">{t.community.title}</span>
      </NavLink>
      <NavLink to="/settings" className="home-link">
        <Icon name="settings" />
        <span className="home-link-text">{t.nav.settings}</span>
        <span className="home-count" aria-hidden>
          {lang.toUpperCase()}
        </span>
      </NavLink>
    </nav>
  );
}
