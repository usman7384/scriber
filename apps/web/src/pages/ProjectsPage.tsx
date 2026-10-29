import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api";
import { Pending } from "../components/Pending";
import { byNewest, date } from "../format";
import { useResource } from "../hooks";
import { useT } from "../i18n";

export function ProjectsPage() {
  const projects = useResource("projects", api.projects);
  const [name, setName] = useState("");
  const [error, setError] = useState<string>();
  const navigate = useNavigate();
  const t = useT();

  const create = (e: FormEvent) => {
    e.preventDefault();
    api.createProject(name.trim()).then(
      (p) => navigate(`/p/${p.id}`),
      (err: Error) => setError(err.message),
    );
  };

  return (
    <section className="stack">
      <div className="page-head">
        <h1>{t.nav.projects}</h1>
        <form onSubmit={create} className="row">
          <label className="sr-only" htmlFor="project-name">
            {t.projects.name}
          </label>
          <input
            id="project-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t.projects.newName}
          />
          <button type="submit" disabled={!name.trim()}>
            {t.projects.create}
          </button>
        </form>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {projects.data ? (
        <ul className="cards">
          {byNewest(projects.data).map((p) => (
            <li key={p.id} className="card">
              <Link to={`/p/${p.id}`} className="card-title">
                {p.name}
              </Link>
              <p className="muted">{t.projects.counts(p.model_count, p.file_count)}</p>
              <p className="muted small">{t.projects.created(date(p.created))}</p>
            </li>
          ))}
          {projects.data.length === 0 && <li className="empty">{t.projects.none}</li>}
        </ul>
      ) : (
        <Pending error={projects.error} />
      )}
    </section>
  );
}
