import { useState, type FormEvent } from "react";
import { Link, NavLink, useNavigate } from "react-router";
import { api, type Project } from "../api";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { Icon } from "../ui/icons";

export function ProjectList({ projects, allCurrent }: { projects: Project[]; allCurrent: boolean }) {
  const t = useT().home;
  const total = projects.reduce((n, p) => n + p.model_count, 0);
  return (
    <ul className="home-projects">
      <li>
        <Link to="/library" className="home-link" aria-current={allCurrent ? "page" : undefined}>
          <Icon name="grid" />
          <span className="home-link-text">{t.allParts}</span>
          <span className="home-count" aria-hidden>
            {total}
          </span>
        </Link>
      </li>
      {projects.map((p) => (
        <li key={p.id}>
          <NavLink to={`/p/${p.id}`} className="home-link">
            <Icon name="part" />
            <span className="home-link-text">{p.name}</span>
            <span className="home-count" aria-hidden>
              {p.model_count}
            </span>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

export function NewProject({ startOpen = false }: { startOpen?: boolean }) {
  const [open, setOpen] = useState(startOpen);
  const [name, setName] = useState("");
  const [error, setError] = useState<string>();
  const navigate = useNavigate();
  const t = useT();

  const create = (e: FormEvent) => {
    e.preventDefault();
    api.createProject(name.trim()).then(
      (p) => {
        setOpen(startOpen);
        setName("");
        navigate(`/p/${p.id}`);
      },
      (err: Error) => setError(err.message),
    );
  };

  if (!open)
    return (
      <button type="button" className="home-link home-new" onClick={() => setOpen(true)}>
        <Icon name="plus" />
        <span className="home-link-text">{t.home.newProject}</span>
      </button>
    );
  return (
    <form className="home-new-form" onSubmit={create}>
      <input
        aria-label={t.projects.name}
        placeholder={t.projects.name}
        value={name}
        autoFocus
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && !startOpen && setOpen(false)}
      />
      <Button type="submit" variant="primary" disabled={!name.trim()}>
        {t.projects.create}
      </Button>
      {error && (
        <p role="alert" className="home-error">
          {error}
        </p>
      )}
    </form>
  );
}
