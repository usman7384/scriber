import { Link } from "react-router";
import { apiUrl, type Model } from "../api";
import { byNewest, date } from "../format";

export function ModelGallery({ models }: { models: Model[] }) {
  if (models.length === 0)
    return <p className="empty">No models yet. Describe a part above to generate one.</p>;
  return (
    <ul className="gallery" aria-label="Models">
      {byNewest(models).map((m) => (
        <li key={m.id} className="card">
          <Link to={`/m/${m.id}`} className="thumb-link">
            {m.thumbnail_url ? (
              <img src={apiUrl(m.thumbnail_url)} alt="" className="thumb" />
            ) : (
              <div className="thumb placeholder" aria-hidden />
            )}
            <span className="card-title">{m.title}</span>
          </Link>
          <p className="muted small">
            v{m.latest_version} · {date(m.created)}
          </p>
        </li>
      ))}
    </ul>
  );
}
