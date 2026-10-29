export type Vec3 = [number, number, number];
export type Process = "any" | "milling_3axis" | "fdm" | "sla" | "sls";
export type ExportFormat = "step" | "stl" | "glb" | "py" | "ir" | "fcstd";

export interface Project {
  id: string;
  name: string;
  created: string;
  model_count: number;
  file_count: number;
}

export interface ContextFile {
  id: string;
  project_id: string;
  name: string;
  kind: string;
  role: string;
  status: "processing" | "processed" | "failed";
  error?: string | null;
  facts: number;
  rules: number;
  uploaded: string;
  used_in: string[];
}

export interface Fact {
  id: string;
  file_id: string;
  kind: string;
  name: string;
  value: string | number;
  unit: string | null;
  tol?: string | number | null;
  count?: number | null;
  page: number;
  line: number;
  text: string;
  ref: string;
}

export interface Rule {
  id: string;
  kind: string;
  value: number;
  unit: string;
  process: string;
  severity: string;
  binding: string;
  text: string;
  source_ref?: string | null;
}

export interface Model {
  id: string;
  project_id: string;
  title: string;
  created: string;
  latest_version: number | null;
  versions: number;
  thumbnail_url?: string | null;
  forked_from?: ForkSource | null;
}

export interface ForkSource {
  publication: string;
  model_id: string;
  version: number;
  title: string;
  author: string;
}

export interface Publication {
  id: string;
  model_id: string;
  version: number;
  title: string;
  author: string;
  created: string;
  thumbnail_url: string | null;
}

export interface Param {
  name: string;
  label: string;
  value: number;
  unit: string;
  min?: number | null;
  max?: number | null;
  description: string;
  provenance: { source: string; ref?: string | null; quote?: string | null };
}

export interface Check {
  description: string;
  passed: boolean;
  actual: string | number | null;
}

export interface Finding {
  rule_id: string;
  severity: string;
  binding: string;
  message: string;
  part?: string | null;
  measured?: number | null;
  required?: number | null;
  location?: { point: Vec3; face?: string | null } | null;
  suggestion?: string | null;
}

export interface Version {
  model_id: string;
  number: number;
  created: string;
  status: "ok" | "failed";
  origin:
    "generate" | "refine" | "edit" | "params" | "restore" | "context" | "variant" | "suggestion" | "fork";
  prompt?: string | null;
  params: Param[];
  checks: Check[];
  findings: Finding[];
  metrics: { bbox: Vec3; volume: number; mass_g?: number | null; holes: number } | null;
  files: Partial<Record<ExportFormat, string>>;
  thumbnail_url?: string | null;
}

export interface Step {
  kind: string;
  message: string;
  attempt: number;
  elapsed_ms: number;
  progress?: number;
  thumbnail_url?: string | null;
}

export interface Job {
  id: string;
  kind: "generate" | "refine" | "edit" | "params" | "ingest" | "batch";
  status: "queued" | "running" | "done" | "failed";
  project_id: string;
  model_id?: string | null;
  version?: number | null;
  error?: string | null;
  created: string;
  started?: string | null;
  finished?: string | null;
  steps: Step[];
}

export interface Component {
  id: string;
  name: string;
  material: string | null;
  parent: string | null;
  joint: string | null;
}

export interface Suggestion {
  id: string;
  target: string;
  change: Record<string, number>;
  rationale: string;
  status: "open" | "accepted" | "ignored";
}

export interface FacePick {
  point: Vec3;
  normal: Vec3;
  version: number;
}

export interface FaceDriver {
  part: string;
  feature: string;
  param: string;
  rate: number;
}

export interface SharedModel extends Model {
  version: Version;
}

export interface GraphView {
  nodes: { id: string; type: string; name: string }[];
  edges: { src: string; dst: string; type: string }[];
  counts: Record<string, number>;
}

export interface KbStats {
  files: number;
  facts: number;
  rules: number;
  entities: number;
  relations: number;
  generations: number;
  used_in_generation: number;
  score: number;
  level: number;
  next_level_score: number;
}

export interface GenerateRequest {
  prompt: string;
  process?: Process;
  attachments?: string[];
  context_ids?: string[];
}

export interface BugReport {
  model_id: string;
  version: number;
  text: string;
  screenshot?: string;
}

export interface Health {
  status: string;
  model: string;
  ollama: boolean;
  tools: { freecad: boolean; prusaslicer: boolean };
}

export interface Printability {
  model_id: string;
  version: number;
  ok: boolean;
  exit_code: number;
  manifold: boolean;
  layers: number;
  gcode_bytes: number;
  warnings: string[];
  errors: string[];
}

export const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export const apiUrl = (path: string) => (/^(https?:|data:|blob:)/.test(path) ? path : API_BASE + path);

async function send(path: string, init?: RequestInit): Promise<Response> {
  const headers = init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" };
  const res = await fetch(apiUrl(path), { headers, ...init });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(typeof body?.detail === "string" ? body.detail : `${res.status} ${res.statusText}`);
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, init);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (name: string) => post<Project>("/projects", { name }),
  models: (projectId: string) => request<Model[]>(`/projects/${projectId}/models`),
  activeJobs: (projectId: string) => request<Job[]>(`/projects/${projectId}/jobs?active=true`),
  context: (projectId: string) =>
    request<{ files: ContextFile[]; stats: KbStats }>(`/projects/${projectId}/context`),
  upload: (projectId: string, files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files[]", f));
    return request<Job[]>(`/projects/${projectId}/context`, { method: "POST", body: form });
  },
  // XMLHttpRequest because fetch reports no upload progress.
  uploadWithProgress: (projectId: string, file: File, onProgress: (percent: number) => void) =>
    new Promise<Job[]>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const form = new FormData();
      form.append("files[]", file);
      xhr.open("POST", apiUrl(`/projects/${projectId}/context`));
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((100 * e.loaded) / e.total));
      xhr.onload = () => {
        try {
          const body = JSON.parse(xhr.responseText) as unknown;
          if (xhr.status < 300) return resolve(body as Job[]);
          const detail = (body as { detail?: unknown } | null)?.detail;
          reject(new Error(typeof detail === "string" ? detail : `${xhr.status} ${xhr.statusText}`));
        } catch {
          reject(new Error(`${xhr.status} ${xhr.statusText}`));
        }
      };
      xhr.onerror = () => reject(new Error(`upload of ${file.name} failed`));
      xhr.send(form);
    }),
  facts: (projectId: string, fileId: string) =>
    request<Fact[]>(`/projects/${projectId}/context/${fileId}/facts`),
  deleteFile: (projectId: string, fileId: string) =>
    request<undefined>(`/projects/${projectId}/context/${fileId}`, { method: "DELETE" }),
  rules: (projectId: string) => request<Rule[]>(`/projects/${projectId}/rules`),
  graph: (projectId: string) => request<GraphView>(`/projects/${projectId}/graph`),
  generate: (projectId: string, body: GenerateRequest) => post<Job>(`/projects/${projectId}/generate`, body),
  model: (id: string) => request<Model>(`/models/${id}`),
  versions: (id: string) => request<Version[]>(`/models/${id}/versions`),
  restore: (id: string, n: number) => post<Version>(`/models/${id}/versions/${n}/restore`),
  refine: (id: string, body: { instruction: string; target?: string; process?: Process }) =>
    post<Job>(`/models/${id}/refine`, body),
  setParams: (id: string, values: Record<string, number>) =>
    request<Job>(`/models/${id}/params`, { method: "PATCH", body: JSON.stringify({ values }) }),
  components: (id: string, version: number) =>
    request<Component[]>(`/models/${id}/components?version=${version}`),
  exportFile: async (id: string, fmt: ExportFormat, version: number) => {
    const res = await send(`/models/${id}/export?fmt=${fmt}&version=${version}`);
    const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1];
    return { blob: await res.blob(), name: name ?? `${id}-v${version}.${fmt}` };
  },
  slice: (id: string, version: number) => post<Printability>(`/models/${id}/slice?version=${version}`),
  faceDriver: (id: string, pick: FacePick) => post<FaceDriver>(`/models/${id}/face-driver`, pick),
  suggestions: (id: string) => request<Suggestion[]>(`/models/${id}/suggestions`),
  suggest: (id: string) => post<Suggestion[]>(`/models/${id}/suggestions`),
  acceptSuggestion: (id: string, sid: string) => post<Job>(`/models/${id}/suggestions/${sid}/accept`),
  ignoreSuggestion: (id: string, sid: string) => post<Suggestion>(`/models/${id}/suggestions/${sid}/ignore`),
  share: (modelId: string, version: number) =>
    post<{ id: string; url: string }>("/shares", { model_id: modelId, version }),
  shared: (shareId: string) => request<SharedModel>(`/s/${shareId}`),
  revokeShare: (shareId: string) => request<undefined>(`/shares/${shareId}`, { method: "DELETE" }),
  reportBug: (report: BugReport) => post<unknown>("/bugs", report),
  community: () => request<Publication[]>("/community"),
  publish: (modelId: string, version: number) =>
    post<Publication>("/community", { model_id: modelId, version }),
  fork: (publicationId: string, projectId: string) =>
    post<Model>(`/community/${publicationId}/fork`, { project_id: projectId }),
};

export const exportUrl = (modelId: string, fmt: ExportFormat, version: number) =>
  apiUrl(`/models/${modelId}/export?fmt=${fmt}&version=${version}`);

export interface JobHandlers {
  onStep: (step: Step) => void;
  onEnd: (job: Job) => void;
  onError: (message: string) => void;
}

export function streamJob(jobId: string, handlers: JobHandlers): () => void {
  const source = new EventSource(apiUrl(`/jobs/${jobId}/events`));
  const end = (e: MessageEvent<string>) => {
    source.close();
    handlers.onEnd(JSON.parse(e.data) as Job);
  };
  source.addEventListener("step", (e) => handlers.onStep(JSON.parse(e.data) as Step));
  source.addEventListener("done", end);
  source.addEventListener("failed", end);
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) handlers.onError("Lost the job event stream");
  };
  return () => source.close();
}

export const waitForJob = (jobId: string, onStep: (step: Step) => void = () => undefined) =>
  new Promise<Job>((resolve, reject) => {
    streamJob(jobId, { onStep, onEnd: resolve, onError: (m) => reject(new Error(m)) });
  });
