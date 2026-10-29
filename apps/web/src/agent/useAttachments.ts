import { useRef, useState } from "react";
import { api, waitForJob } from "../api";

export type AttachKind = "image" | "mesh" | "spec";

export interface Attachment {
  key: number;
  file: File;
  kind: AttachKind;
  status: "uploading" | "reading" | "ready" | "failed";
  progress: number;
  id?: string;
  facts?: number;
  error?: string;
}

type Patch = Partial<Omit<Attachment, "key" | "file" | "kind">>;

const meshes = /\.(stl|obj|step|stp|iges|igs|glb|gltf|3mf|fcstd)$/i;

export const kindOf = (file: File): AttachKind =>
  file.type.startsWith("image/") ? "image" : meshes.test(file.name) ? "mesh" : "spec";

async function ingest(projectId: string, file: File, set: (p: Patch) => void): Promise<string> {
  const [job] = await api.uploadWithProgress(projectId, file, (progress) => set({ progress }));
  if (!job) throw new Error(`no ingest job for ${file.name}`);
  set({ status: "reading", progress: 0 });
  const end = await waitForJob(job.id, (s) => set({ progress: s.progress ?? 0 }));
  if (end.status !== "done") throw new Error(end.error ?? end.status);
  const { files } = await api.context(projectId);
  const stored = files
    .filter((f) => f.name === file.name)
    .sort((a, b) => b.uploaded.localeCompare(a.uploaded))[0];
  if (!stored) throw new Error(`${file.name} is not in the project context`);
  if (stored.status === "failed") throw new Error(stored.error ?? stored.status);
  set({ status: "ready", progress: 100, id: stored.id, facts: stored.facts });
  return stored.id;
}

export function useAttachments(projectId: string) {
  const [items, setItems] = useState<Attachment[]>([]);
  const next = useRef(0);
  const pending = useRef(new Map<number, Promise<void>>());
  const ready = useRef(new Map<number, string>());
  const live = useRef(new Set<number>());

  const patch = (key: number, p: Patch) =>
    setItems((all) => all.map((a) => (a.key === key ? { ...a, ...p } : a)));

  const start = (key: number, file: File) => {
    const run = ingest(projectId, file, (p) => live.current.has(key) && patch(key, p)).then(
      (id) => void (live.current.has(key) && ready.current.set(key, id)),
      (e: unknown) => patch(key, { status: "failed", error: e instanceof Error ? e.message : String(e) }),
    );
    pending.current.set(key, run);
    void run.finally(() => pending.current.get(key) === run && pending.current.delete(key));
  };

  const add = (files: File[]) => {
    const added = files.map((file): Attachment => {
      const key = next.current++;
      live.current.add(key);
      return { key, file, kind: kindOf(file), status: "uploading", progress: 0 };
    });
    setItems((all) => [...all, ...added]);
    added.forEach((a) => start(a.key, a.file));
  };

  const retry = (a: Attachment) => {
    patch(a.key, { status: "uploading", progress: 0, error: undefined });
    start(a.key, a.file);
  };

  const remove = (key: number) => {
    live.current.delete(key);
    ready.current.delete(key);
    pending.current.delete(key);
    setItems((all) => all.filter((a) => a.key !== key));
  };

  const clear = () => items.forEach((a) => remove(a.key));

  // Ids of every attachment that ends ready, in the order they were added; failed ones block nothing.
  const settled = async () => {
    await Promise.all(pending.current.values());
    return [...ready.current].sort(([a], [b]) => a - b).map(([, id]) => id);
  };

  const busy = items.some((a) => a.status === "uploading" || a.status === "reading");
  return { items, busy, add, retry, remove, clear, settled };
}
