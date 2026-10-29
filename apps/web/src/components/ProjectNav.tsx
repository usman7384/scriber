import { NavLink } from "react-router";
import type { Project } from "../api";
import { useT } from "../i18n";

export function ProjectNav({ project }: { project: Project }) {
  const t = useT().project;
  return (
    <div className="page-head">
      <h1>{project.name}</h1>
      <nav aria-label={t.tabs} className="tabs">
        <NavLink to={`/p/${project.id}`} end>
          {t.models}
        </NavLink>
        <NavLink to={`/p/${project.id}/context`}>{t.context}</NavLink>
      </nav>
    </div>
  );
}
