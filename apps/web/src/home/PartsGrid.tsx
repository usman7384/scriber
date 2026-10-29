import { useState, type ReactNode } from "react";
import { Link } from "react-router";
import { apiUrl } from "../api";
import { byNewest } from "../format";
import { useT } from "../i18n";
import { Icon } from "../ui/icons";

export interface Part {
  id: string;
  title: string;
  created: string;
  thumbnail?: string | null | undefined;
  href?: string;
  meta: ReactNode;
  action?: ReactNode;
}

type Sort = "newest" | "name";

const sorted = (parts: Part[], sort: Sort) =>
  sort === "newest" ? byNewest(parts) : [...parts].sort((a, b) => a.title.localeCompare(b.title));

export function PartsGrid({ label, parts, empty }: { label: string; parts: Part[]; empty: string }) {
  const [sort, setSort] = useState<Sort>("newest");
  const t = useT().home;
  return (
    <section className="parts">
      <header className="parts-bar">
        <h2>{t.parts}</h2>
        <select aria-label={t.sort} value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
          {(Object.keys(t.sorts) as Sort[]).map((s) => (
            <option key={s} value={s}>
              {t.sorts[s]}
            </option>
          ))}
        </select>
      </header>
      {parts.length === 0 ? (
        <p className="home-empty">{empty}</p>
      ) : (
        <ul className="parts-grid" aria-label={label}>
          {sorted(parts, sort).map((p) => (
            <li key={p.id} className="part-card">
              <div className="part-thumb">
                {p.thumbnail ? <img src={apiUrl(p.thumbnail)} alt="" /> : <Icon name="part" size={32} />}
              </div>
              <div className="part-body">
                {p.href ? (
                  <Link to={p.href} className="card-title part-link">
                    {p.title}
                  </Link>
                ) : (
                  <span className="card-title">{p.title}</span>
                )}
                {p.meta}
                {p.action}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
