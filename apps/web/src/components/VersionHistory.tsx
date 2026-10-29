import { apiUrl, type Version } from "../api";
import { date } from "../format";
import { useT } from "../i18n";

interface Props {
  versions: Version[];
  selected: number;
  latest: number;
  onSelect: (n: number) => void;
  onRestore: (n: number) => void;
}

export function VersionHistory({ versions, selected, latest, onSelect, onRestore }: Props) {
  const t = useT();
  return (
    <ol className="versions" aria-label={t.editor.versions} reversed>
      {[...versions].reverse().map((v) => (
        <li key={v.number} className={v.number === selected ? "selected" : undefined}>
          <button
            type="button"
            className="version"
            aria-current={v.number === selected}
            onClick={() => onSelect(v.number)}
          >
            {v.thumbnail_url && <img src={apiUrl(v.thumbnail_url)} alt="" width={48} height={48} />}
            <span>
              <strong>v{v.number}</strong> <span className="badge">{t.origin[v.origin] ?? v.origin}</span>
              {v.prompt && <span className="small clamp">{v.prompt}</span>}
              <span className="muted small">{date(v.created)}</span>
            </span>
          </button>
          {v.number !== latest && (
            <button type="button" className="secondary small" onClick={() => onRestore(v.number)}>
              {t.editor.restore(v.number)}
            </button>
          )}
        </li>
      ))}
    </ol>
  );
}
