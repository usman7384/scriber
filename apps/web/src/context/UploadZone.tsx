import { useState, type DragEvent } from "react";
import { api, waitForJob } from "../api";
import { useT } from "../i18n";

interface Upload {
  name: string;
  status: "uploading" | "processing" | "processed" | "failed";
  error?: string | null | undefined;
  progress: number;
}

export function UploadZone({ projectId, onChange }: { projectId: string; onChange: () => void }) {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [over, setOver] = useState(false);
  const t = useT();

  const set = (name: string, patch: Partial<Upload>) =>
    setUploads((all) => all.map((u) => (u.name === name ? { ...u, ...patch } : u)));

  const add = async (files: File[]) => {
    if (files.length === 0) return;
    setUploads((all) => [
      ...files.map((f): Upload => ({ name: f.name, status: "uploading", progress: 0 })),
      ...all,
    ]);
    try {
      const jobs = await api.upload(projectId, files);
      onChange();
      await Promise.all(
        files.map(async (f, i) => {
          const job = jobs[i];
          if (!job) return set(f.name, { status: "failed", error: t.context.noJob });
          set(f.name, { status: "processing" });
          const end = await waitForJob(job.id, (s) => set(f.name, { progress: s.progress ?? 0 }));
          set(f.name, { status: end.status === "done" ? "processed" : "failed", error: end.error });
          onChange();
        }),
      );
    } catch (e) {
      files.forEach((f) => set(f.name, { status: "failed", error: (e as Error).message }));
    }
  };

  const drop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    void add([...e.dataTransfer.files]);
  };

  return (
    <div className="stack">
      <div
        className={`dropzone${over ? " over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
      >
        <p>{t.context.drop}</p>
        <label className="button secondary">
          {t.context.choose}
          <input
            type="file"
            multiple
            className="sr-only"
            onChange={(e) => void add([...(e.target.files ?? [])])}
          />
        </label>
      </div>
      {uploads.length > 0 && (
        <ul className="list" aria-label={t.context.uploads}>
          {uploads.map((u, i) => (
            <li key={i} className="row">
              <span>{u.name}</span>
              <progress value={u.progress} max={100} aria-label={t.context.progress(u.name)} />
              <span className={`badge ${u.status}`}>{t.status[u.status] ?? u.status}</span>
              {u.error && <span className="error small">{u.error}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
