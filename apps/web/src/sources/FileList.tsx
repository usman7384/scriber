import { useState } from "react";
import { Link } from "react-router";
import type { ContextFile } from "../api";
import { date } from "../format";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { Icon } from "../ui/icons";
import { FileStatus } from "./FileStatus";

interface Props {
  files: ContextFile[];
  open?: string | undefined;
  chosen?: string[];
  titles?: Record<string, string>;
  onOpen: (id: string) => void;
  onChoose?: (ids: string[]) => void;
  onDelete: (id: string) => void;
}

export function FileList({ files, open, chosen = [], titles = {}, onOpen, onChoose, onDelete }: Props) {
  const [query, setQuery] = useState("");
  const [confirming, setConfirming] = useState<string>();
  const t = useT().context;
  const shown = files.filter((f) => f.name.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <label className="src-search">
        <Icon name="search" />
        <input
          type="search"
          aria-label={t.search}
          placeholder={t.search}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <table className="src-files" aria-label={t.table}>
        <thead className="sr-only">
          <tr>
            {t.columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
            <th>{t.actions}</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((f) => (
            <tr key={f.id} aria-selected={f.id === open}>
              <td>
                {onChoose && (
                  <input
                    type="checkbox"
                    aria-label={t.useAs(f.name)}
                    checked={chosen.includes(f.id)}
                    onChange={(e) =>
                      onChoose(e.target.checked ? [...chosen, f.id] : chosen.filter((id) => id !== f.id))
                    }
                  />
                )}
                <button type="button" className="src-name" title={f.name} onClick={() => onOpen(f.id)}>
                  {f.name}
                </button>
              </td>
              <td className="mono">{f.kind.toUpperCase()}</td>
              <td>
                <FileStatus status={f.status} error={f.error} />
              </td>
              <td>{t.factCount(f.facts)}</td>
              <td>
                {f.used_in.length === 0
                  ? "—"
                  : f.used_in.map((id) => (
                      <Link key={id} to={`/m/${id}`}>
                        {titles[id] ?? id}
                      </Link>
                    ))}
              </td>
              <td>{date(f.uploaded)}</td>
              <td>
                {confirming === f.id ? (
                  <Button className="src-danger" onClick={() => onDelete(f.id)}>
                    {t.confirmDelete}
                  </Button>
                ) : (
                  <IconButton
                    icon="trash"
                    label={`${t.delete} ${f.name}`}
                    onClick={() => setConfirming(f.id)}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {shown.length === 0 && <p className="src-empty">{files.length ? t.noMatch : t.noFiles}</p>}
    </>
  );
}
