import { useState } from "react";
import type { ContextFile } from "../api";
import { date } from "../format";

interface Props {
  files: ContextFile[];
  open?: string | undefined;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}

export function FileTable({ files, open, onOpen, onDelete }: Props) {
  const [query, setQuery] = useState("");
  const [confirming, setConfirming] = useState<string>();
  const shown = files.filter((f) => f.name.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <div className="stack">
      <input
        type="search"
        aria-label="Search files"
        placeholder="Search files"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="table-wrap">
        <table aria-label="Context files">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Facts</th>
              <th>Used in</th>
              <th>Uploaded</th>
              <th>
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {shown.map((f) => (
              <tr key={f.id} aria-selected={f.id === open}>
                <td>
                  <button type="button" className="link" onClick={() => onOpen(f.id)}>
                    {f.name}
                  </button>
                </td>
                <td>{f.kind}</td>
                <td>
                  <span className={`badge ${f.status}`} title={f.error ?? undefined}>
                    {f.status}
                  </span>
                </td>
                <td>{f.facts}</td>
                <td>{f.used_in.length} models</td>
                <td>{date(f.uploaded)}</td>
                <td>
                  {confirming === f.id ? (
                    <button type="button" className="danger small" onClick={() => onDelete(f.id)}>
                      Confirm delete
                    </button>
                  ) : (
                    <button type="button" className="secondary small" onClick={() => setConfirming(f.id)}>
                      Delete <span className="sr-only">{f.name}</span>
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown.length === 0 && (
        <p className="empty">{files.length ? "No files match the search." : "No context files yet."}</p>
      )}
    </div>
  );
}
