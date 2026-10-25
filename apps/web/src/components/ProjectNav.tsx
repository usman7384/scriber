import { NavLink } from "react-router";
import type { Project } from "../api";

export function ProjectNav({ project }: { project: Project }) {
  return (
    <div className="page-head">
      <h1>{project.name}</h1>
      <nav aria-label="Project" className="tabs">
        <NavLink to={`/p/${project.id}`} end>
          Models
        </NavLink>
        <NavLink to={`/p/${project.id}/context`}>Context</NavLink>
      </nav>
    </div>
  );
}
