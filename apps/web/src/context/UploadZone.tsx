import { useState, type DragEvent } from "react";
import { api, waitForJob } from "../api";

interface Upload {
  name: string;
  status: "uploading" | "processing" | "processed" | "failed";
  error?: string | null | undefined;
}

export function UploadZone({ projectId, onChange }: { projectId: string; onChange: () => void }) {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [over, setOver] = useState(false);

  const set = (name: string, patch: Partial<Upload>) =>
    setUploads((all) => all.map((u) => (u.name === name ? { ...u, ...patch } : u)));

  const add = async (files: File[]) => {
    if (files.length === 0) return;
    setUploads((all) => [...files.map((f): Upload => ({ name: f.name, status: "uploading" })), ...all]);
    try {
      const jobs = await api.upload(projectId, files);
      onChange();
      await Promise.all(
        files.map(async (f, i) => {
          const job = jobs[i];
          if (!job) return set(f.name, { status: "failed", error: "No ingest job returned" });
          set(f.name, { status: "processing" });
          const end = await waitForJob(job.id);
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
        <p>Drop specs, drawings, CAD files, images or tables here</p>
        <label className="button secondary">
          Choose files
          <input
            type="file"
            multiple
            className="sr-only"
            onChange={(e) => void add([...(e.target.files ?? [])])}
          />
        </label>
      </div>
      {uploads.length > 0 && (
        <ul className="list" aria-label="Uploads">
          {uploads.map((u, i) => (
            <li key={i} className="row">
              <span>{u.name}</span>
              <span className={`badge ${u.status}`}>{u.status}</span>
              {u.error && <span className="error small">{u.error}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
