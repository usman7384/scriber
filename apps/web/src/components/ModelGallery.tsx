import { Link } from "react-router";
import { apiUrl, type Model } from "../api";
import { byNewest, date } from "../format";
import { useT } from "../i18n";

export function ModelGallery({ models }: { models: Model[] }) {
  const t = useT().gallery;
  if (models.length === 0) return <p className="empty">{t.none}</p>;
  return (
    <ul className="gallery" aria-label={t.region}>
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
            {m.latest_version === null ? t.noVersion : `v${m.latest_version}`} · {date(m.created)}
          </p>
        </li>
      ))}
    </ul>
  );
}
