import { readFileSync } from "node:fs";
import type { Page, Request, Route } from "@playwright/test";
import type { Job, Model, Step, Version } from "../src/api";
import { contextFiles, firstVersion, graph, now, project, thumbnail } from "./fixtures";

const glb = readFileSync(new URL("./fixtures/plate.glb", import.meta.url));
const apiPath = /^\/(projects|models|jobs|shares|bugs)(\/|$)/;

type Reply = Parameters<Route["fulfill"]>[0];
type Handler = (m: RegExpMatchArray, req: Request) => Reply;

const json = (body: unknown, status = 200): Reply => ({ status, json: body });

const sse = (steps: Step[], job: Job): Reply => ({
  status: 200,
  headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  body:
    steps.map((s) => `event: step\ndata: ${JSON.stringify(s)}\n\n`).join("") +
    `event: ${job.status}\ndata: ${JSON.stringify(job)}\n\n`,
});

export class MockApi {
  models: Model[] = [];
  versions: Version[] = [];
  files = [...contextFiles];
  requests: { method: string; path: string; body: unknown }[] = [];
  private jobs = new Map<string, () => Reply>();

  private job(kind: Job["kind"], run: () => Version | undefined, steps: Step[]): Job {
    const id = `${kind}-${this.jobs.size + 1}`;
    const base: Job = { id, kind, status: "queued", project_id: "p1", created: now(5), steps: [] };
    this.jobs.set(id, () => {
      const v = run();
      return sse(steps, { ...base, status: "done", model_id: "m1", version: v?.number ?? null, steps });
    });
    return base;
  }

  private addVersion(v: Version) {
    this.versions.push(v);
    const model = this.models[0];
    if (model) Object.assign(model, { latest_version: v.number, versions: this.versions.length });
    return v;
  }

  private derive(from: Version, over: Partial<Version>) {
    const number = this.versions.length + 1;
    return this.addVersion({ ...from, number, created: now(10 + number), prompt: null, ...over });
  }

  private routes: [string, RegExp, Handler][] = [
    ["GET", /^\/projects$/, () => json([{ ...project, model_count: this.models.length }])],
    ["GET", /^\/projects\/p1$/, () => json(project)],
    ["GET", /^\/projects\/p1\/models$/, () => json(this.models)],
    [
      "POST",
      /^\/projects\/p1\/generate$/,
      () =>
        json(
          this.job(
            "generate",
            () => {
              this.models = [
                {
                  id: "m1",
                  project_id: "p1",
                  title: "Sensor plate",
                  created: now(1),
                  latest_version: 1,
                  versions: 1,
                  thumbnail_url: "/models/m1/thumbnail.svg",
                },
              ];
              return this.addVersion(firstVersion());
            },
            [
              {
                kind: "requirements",
                message: "REQ-1 Plate size 120 x 80 x 6 mm",
                attempt: 0,
                elapsed_ms: 500,
              },
              { kind: "emit", message: "answer of 1984 chars", attempt: 1, elapsed_ms: 17281 },
              {
                kind: "check",
                message: "holes overlap; spread the hole centres apart",
                attempt: 1,
                elapsed_ms: 17300,
              },
              { kind: "repair", message: "answer of 1949 chars", attempt: 2, elapsed_ms: 34687 },
              {
                kind: "done",
                message: "all checks pass",
                attempt: 2,
                elapsed_ms: 35200,
                thumbnail_url: "/models/m1/thumbnail.svg",
              },
            ],
          ),
        ),
    ],
    [
      "GET",
      /^\/jobs\/([\w-]+)\/events$/,
      (m) => this.jobs.get(m[1] ?? "")?.() ?? json({ detail: "no job" }, 404),
    ],
    ["GET", /^\/models\/m1$/, () => json(this.models[0])],
    ["GET", /^\/models\/m1\/versions$/, () => json(this.versions)],
    ["GET", /^\/models\/m1\/export$/, () => ({ status: 200, contentType: "model/gltf-binary", body: glb })],
    [
      "GET",
      /^\/models\/m1\/thumbnail\.svg$/,
      () => ({ status: 200, contentType: "image/svg+xml", body: thumbnail }),
    ],
    [
      "PATCH",
      /^\/models\/m1\/params$/,
      (_, req) => {
        const { values } = req.postDataJSON() as { values: Record<string, number> };
        const steps: Step[] = [
          { kind: "done", message: "rebuilt without the LLM", attempt: 0, elapsed_ms: 640 },
        ];
        return json(
          this.job(
            "params",
            () => {
              const last = this.versions.at(-1) ?? firstVersion();
              const params = last.params.map((p) => ({ ...p, value: values[p.name] ?? p.value }));
              return this.derive(last, { origin: "params", params });
            },
            steps,
          ),
        );
      },
    ],
    [
      "POST",
      /^\/models\/m1\/versions\/(\d+)\/restore$/,
      (m) => {
        const from = this.versions.find((v) => v.number === Number(m[1]));
        return from ? json(this.derive(from, { origin: "restore" })) : json({ detail: "no version" }, 404);
      },
    ],
    [
      "POST",
      /^\/models\/m1\/refine$/,
      (_, req) => {
        const { instruction } = req.postDataJSON() as { instruction: string };
        const steps: Step[] = [
          { kind: "done", message: "1 parameter changed", attempt: 1, elapsed_ms: 9100 },
        ];
        const last = () => this.versions.at(-1) ?? firstVersion();
        return json(
          this.job("refine", () => this.derive(last(), { origin: "refine", prompt: instruction }), steps),
        );
      },
    ],
    ["POST", /^\/shares$/, () => json({ id: "s1", url: "/s/s1" })],
    ["GET", /^\/projects\/p1\/context$/, () => json({ files: this.files, stats: this.stats() })],
    [
      "DELETE",
      /^\/projects\/p1\/context\/(\w+)$/,
      (m) => {
        this.files = this.files.filter((f) => f.id !== m[1]);
        return { status: 204 };
      },
    ],
    [
      "GET",
      /^\/projects\/p1\/rules$/,
      () =>
        json([
          {
            id: "r1",
            kind: "min_hole_edge_ratio",
            value: 2,
            unit: "x D",
            process: "milling_3axis",
            severity: "error",
            binding: "static",
            text: "Hole-to-edge distance at least 2 x D",
            source_ref: "plate-design-rules.md:4",
          },
        ]),
    ],
    ["GET", /^\/projects\/p1\/graph$/, () => json(graph)],
    [
      "GET",
      /^\/projects\/p1\/context\/(\w+)\/facts$/,
      (m) =>
        json([
          {
            id: "x1",
            file_id: m[1],
            kind: "dimension",
            name: "plate length",
            value: 120,
            unit: "mm",
            page: 1,
            line: 2,
            text: "REQ-1 Plate size 120 x 80 x 6 mm",
            ref: "p1:l2",
          },
        ]),
    ],
  ];

  private stats() {
    return {
      files: this.files.length,
      facts: 21,
      rules: 2,
      entities: graph.nodes.length,
      relations: graph.edges.length,
      generations: this.models.length,
      used_in_generation: 1,
      score: 34,
      level: 1,
      next_level_score: 50,
    };
  }

  async install(page: Page) {
    await page.route(
      (url) => apiPath.test(url.pathname),
      (route) => {
        const req = route.request();
        const { pathname } = new URL(req.url());
        this.requests.push({
          method: req.method(),
          path: pathname,
          body: req.postData() ? req.postDataJSON() : null,
        });
        for (const [method, pattern, handler] of this.routes) {
          const m = pathname.match(pattern);
          if (m && method === req.method()) return route.fulfill(handler(m, req));
        }
        return route.fulfill(json({ detail: `unmocked ${req.method()} ${pathname}` }, 404));
      },
    );
  }
}
