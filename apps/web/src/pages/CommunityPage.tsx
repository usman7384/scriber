import { useState } from "react";
import { Link } from "react-router";
import { api, apiUrl, type Model } from "../api";
import { Pending } from "../components/Pending";
import { date } from "../format";
import { useResource } from "../hooks";
import { useT } from "../i18n";

export function CommunityPage() {
  const published = useResource("community", api.community);
  const projects = useResource("projects", api.projects);
  const [picked, setPicked] = useState<string>();
  const [fork, setFork] = useState<Model>();
  const [error, setError] = useState<string>();
  const t = useT().community;
  if (!published.data || !projects.data) return <Pending error={published.error ?? projects.error} />;
  const target = picked ?? projects.data[0]?.id;
  const copy = (publicationId: string) => {
    if (!target) return;
    setError(undefined);
    api.fork(publicationId, target).then(setFork, (e: Error) => setError(e.message));
  };
  const into = projects.data.find((p) => p.id === fork?.project_id)?.name ?? "";
  return (
    <section className="stack">
      <h1>{t.title}</h1>
      <label className="row">
        {t.into}
        <select value={target} onChange={(e) => setPicked(e.target.value)}>
          {projects.data.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      {fork && (
        <p role="status">
          {t.forked(fork.title, into)} <Link to={`/m/${fork.id}`}>{t.open}</Link>
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {published.data.length === 0 ? (
        <p className="empty">{t.none}</p>
      ) : (
        <ul className="gallery" aria-label={t.region}>
          {published.data.map((p) => (
            <li key={p.id} className="card">
              {p.thumbnail_url ? (
                <img src={apiUrl(p.thumbnail_url)} alt="" className="thumb" />
              ) : (
                <div className="thumb placeholder" aria-hidden />
              )}
              <span className="card-title">{p.title}</span>
              <p className="muted small">
                v{p.version} · {t.by(p.author)} · {date(p.created)}
              </p>
              <button
                type="button"
                className="secondary"
                aria-label={t.forkTitle(p.title)}
                disabled={!target}
                onClick={() => copy(p.id)}
              >
                {t.fork}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
