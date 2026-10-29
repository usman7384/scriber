import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, type APIRequestContext } from "@playwright/test";
import type { Job, Version } from "../../src/api";

export const API = process.env.PARTWRIGHT_LIVE_API ?? "http://127.0.0.1:8765";
export const root = fileURLToPath(new URL("../../../../", import.meta.url));
export const repoFile = (path: string) => readFileSync(`${root}${path}`);

export async function project(request: APIRequestContext, name: string): Promise<string> {
  const res = await request.post(`${API}/projects`, { data: { name } });
  expect(res.ok()).toBe(true);
  return ((await res.json()) as { id: string }).id;
}

export async function waitJob(request: APIRequestContext, job: Job): Promise<Job> {
  let current = job;
  while (current.status !== "done" && current.status !== "failed") {
    await new Promise((r) => setTimeout(r, 250));
    current = (await (await request.get(`${API}/jobs/${job.id}`)).json()) as Job;
  }
  return current;
}

// Posts IR to the deterministic build route (no model) and returns the built model id.
export async function build(
  request: APIRequestContext,
  projectId: string,
  design: object,
  status: Job["status"] = "done",
): Promise<string> {
  const res = await request.post(`${API}/projects/${projectId}/designs`, { data: { design } });
  expect(res.ok(), await res.text()).toBe(true);
  const job = await waitJob(request, (await res.json()) as Job);
  expect(job.status, job.error ?? "").toBe(status);
  return job.model_id ?? "";
}

export async function upload(request: APIRequestContext, projectId: string, files: Upload[]) {
  const form = new FormData();
  for (const f of files)
    form.append("files", new Blob([new Uint8Array(f.buffer)], { type: f.mimeType }), f.name);
  const res = await request.post(`${API}/projects/${projectId}/context`, { multipart: form });
  expect(res.ok(), await res.text()).toBe(true);
  for (const job of (await res.json()) as Job[]) expect((await waitJob(request, job)).status).toBe("done");
}

export const versions = async (request: APIRequestContext, modelId: string) =>
  (await (await request.get(`${API}/models/${modelId}/versions`)).json()) as Version[];

export const getJson = async <T>(request: APIRequestContext, path: string) =>
  (await (await request.get(`${API}${path}`)).json()) as T;

// Kernel-side checks (trimesh, PrusaSlicer, section fits) run through the repo's Python environment.
export const kernelCheck = (...args: string[]) =>
  JSON.parse(
    execFileSync("uv", ["run", "python", "apps/web/e2e/live/checks.py", ...args], {
      cwd: root,
      encoding: "utf-8",
    }),
  ) as Record<string, string | number | boolean | null | number[] | string[]>;

export interface Upload {
  name: string;
  mimeType: string;
  buffer: Buffer;
}

export const flat = (m: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(m).map(([k, v]) => [
      k,
      Array.isArray(v) ? v.join(", ") : (v as string | number | boolean | null),
    ]),
  );
