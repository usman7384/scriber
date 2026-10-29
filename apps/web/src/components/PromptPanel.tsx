import { useState, type FormEvent } from "react";
import { api, waitForJob, type ContextFile, type Job, type Process } from "../api";
import { useT } from "../i18n";

const examples = [
  "Mounting plate 100 x 60 x 5 mm with four M5 clearance holes 8 mm from each edge",
  "L-bracket, legs 40 and 30 mm, 4 mm thick, 25 mm wide, two M4 holes per leg",
  "Spacer ring, 30 mm outer diameter, 12 mm bore, 8 mm tall",
  "Electronics box 120 x 80 x 40 mm, 2 mm walls, open top",
];

const kinds = [
  { kind: "image", accept: "image/*" },
  { kind: "mesh", accept: ".stl,.obj,.step,.stp,.glb" },
  { kind: "spec", accept: ".pdf,.md,.txt,.csv" },
] as const;

async function uploadAttachments(projectId: string, files: File[]): Promise<string[]> {
  if (files.length === 0) return [];
  const jobs = await api.upload(projectId, files);
  await Promise.all(jobs.map((j) => waitForJob(j.id)));
  const { files: stored } = await api.context(projectId);
  const newest = [...stored].sort((a, b) => b.uploaded.localeCompare(a.uploaded));
  return files.flatMap((f) => newest.find((s) => s.name === f.name)?.id ?? []);
}

interface Props {
  projectId: string;
  context?: ContextFile[];
  onClearContext?: () => void;
  onJob: (job: Job) => void;
}

export function PromptPanel({ projectId, context = [], onClearContext, onJob }: Props) {
  const [prompt, setPrompt] = useState("");
  const [proc, setProc] = useState<Process>("any");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const t = useT();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const attachments = await uploadAttachments(projectId, files);
      const context_ids = context.length ? { context_ids: context.map((f) => f.id) } : {};
      onJob(
        await api.generate(projectId, { prompt: prompt.trim(), process: proc, attachments, ...context_ids }),
      );
      setFiles([]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="panel prompt" onSubmit={submit} aria-label={t.prompt.form}>
      <label htmlFor="prompt">{t.prompt.label}</label>
      <textarea
        id="prompt"
        rows={4}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={t.prompt.placeholder}
      />
      <div className="chips" aria-label={t.prompt.examples}>
        {examples.map((text) => (
          <button key={text} type="button" className="chip" onClick={() => setPrompt(text)}>
            {text}
          </button>
        ))}
      </div>
      {context.length > 0 && (
        <ul className="attachments" aria-label={t.prompt.context}>
          {context.map((f) => (
            <li key={f.id} className="chip">
              {f.name}
            </li>
          ))}
          <li>
            <button type="button" className="link" onClick={onClearContext}>
              {t.prompt.clearContext}
            </button>
          </li>
        </ul>
      )}
      {files.length > 0 && (
        <ul className="attachments" aria-label={t.prompt.attachments}>
          {files.map((f) => (
            <li key={f.name} className="chip">
              {f.name}
              <button type="button" className="link" onClick={() => setFiles(files.filter((x) => x !== f))}>
                {t.prompt.remove} <span className="sr-only">{f.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="row wrap">
        {kinds.map((k) => (
          <label key={k.kind} className="button secondary">
            + {t.prompt.kinds[k.kind]}
            <input
              type="file"
              className="sr-only"
              accept={k.accept}
              multiple
              onChange={(e) => setFiles([...files, ...(e.target.files ?? [])])}
            />
          </label>
        ))}
        <label className="row">
          {t.prompt.process}
          <select value={proc} onChange={(e) => setProc(e.target.value as Process)}>
            {Object.entries(t.processes).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary push" disabled={busy || !prompt.trim()}>
          {busy ? t.prompt.starting : t.prompt.generate}
        </button>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </form>
  );
}
