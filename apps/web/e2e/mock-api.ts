import type { Page, Request, Route } from "@playwright/test";
import type { BugReport, ContextFile, Job, Model, Step, Version } from "../src/api";
import {
  contextFiles,
  firstVersion,
  graphOf,
  now,
  project,
  sensorPlate,
  shop,
  shopModels,
  shopThumbnails,
  valuesOf,
  versionUrls,
  type Scenario,
} from "./fixtures";

const apiPath = /^\/(projects|models|jobs|shares|bugs)(\/|$)/;

type Reply = Parameters<Route["fulfill"]>[0];
type Handler = (m: RegExpMatchArray, req: Request) => Reply;

const json = (body: unknown, status = 200): Reply => ({ status, json: body });
const png = (body: Buffer): Reply => ({ status: 200, contentType: "image/png", body });
const missing = (what: string) => json({ detail: `no ${what}` }, 404);

const sse = (steps: Step[], job: Job): Reply => ({
  status: 200,
  headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  body:
    steps.map((s) => `event: step\ndata: ${JSON.stringify(s)}\n\n`).join("") +
    `event: ${job.status}\ndata: ${JSON.stringify(job)}\n\n`,
});

const uploadedNames = (req: Request) =>
  [...(req.postDataBuffer()?.toString("latin1") ?? "").matchAll(/filename="([^"]+)"/g)].map(
    (m) => m[1] ?? "",
  );

export class MockApi {
  models: Model[] = [];
  versions: Version[] = [];
  files = [...contextFiles];
  bugs: BugReport[] = [];
  requests: { method: string; path: string; body: unknown; at: number }[] = [];
  private jobs = new Map<string, () => Reply>();

  constructor(private scenario: Scenario = sensorPlate) {}

  seed() {
    const first = firstVersion(this.scenario);
    this.models = [
      {
        id: "m1",
        project_id: "p1",
        title: this.scenario.title,
        created: now(1),
        latest_version: 1,
        versions: 1,
        thumbnail_url: first.thumbnail_url ?? null,
      },
    ];
    this.versions = [];
    return this.addVersion(first);
  }

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
    if (model)
      Object.assign(model, {
        latest_version: v.number,
        versions: this.versions.length,
        thumbnail_url: v.thumbnail_url,
      });
    return v;
  }

  private build(v: Version | undefined) {
    return v && this.scenario.build(valuesOf(v.params));
  }

  private derive(from: Version, over: Partial<Version>) {
    const number = this.versions.length + 1;
    const v = { ...from, ...versionUrls(number), created: now(10 + number), prompt: null, ...over, number };
    return this.addVersion({ ...v, findings: this.build(v)?.findings ?? [] });
  }

  private version(n: string | null | undefined) {
    return this.versions.find((v) => v.number === Number(n));
  }

  private upload(names: string[]): Job[] {
    const added: ContextFile[] = names.map((name, i) => ({
      id: `u${this.files.length + i + 1}`,
      project_id: "p1",
      name,
      kind: name.split(".").pop() ?? "",
      role: "spec",
      status: "processed",
      facts: 1,
      rules: 0,
      uploaded: now(30 + i),
      used_in: [],
    }));
    this.files = [...this.files, ...added];
    const done: Step[] = [{ kind: "done", message: "ingested", attempt: 0, elapsed_ms: 120 }];
    return added.map(() => this.job("ingest", () => undefined, done));
  }

  private routes: [string, RegExp, Handler][] = [
    ["GET", /^\/projects$/, () => json([{ ...project, model_count: this.models.length }, shop])],
    ["GET", /^\/projects\/p1$/, () => json(project)],
    ["GET", /^\/projects\/p2$/, () => json(shop)],
    ["GET", /^\/projects\/p1\/models$/, () => json(this.models)],
    ["GET", /^\/projects\/p2\/models$/, () => json(shopModels)],
    ["GET", /^\/projects\/p\d\/jobs$/, () => json([])],
    [
      "POST",
      /^\/projects\/p1\/generate$/,
      () =>
        json(
          this.job("generate", () => this.seed(), [
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
              thumbnail_url: "/models/m1/versions/1/thumbnail",
            },
          ]),
        ),
    ],
    ["GET", /^\/jobs\/([\w-]+)\/events$/, (m) => this.jobs.get(m[1] ?? "")?.() ?? missing("job")],
    ["GET", /^\/models\/m1$/, () => json(this.models[0])],
    ["GET", /^\/models\/m1\/versions$/, () => json(this.versions)],
    [
      "GET",
      /^\/models\/m1\/export$/,
      (_, req) => {
        const built = this.build(this.version(new URL(req.url()).searchParams.get("version")));
        return built
          ? { status: 200, contentType: "model/gltf-binary", body: built.glb }
          : missing("geometry");
      },
    ],
    [
      "GET",
      /^\/models\/(m\d)\/versions\/(\d+)\/thumbnail$/,
      (m) => {
        const thumb = m[1] === "m1" ? this.build(this.version(m[2]))?.thumbnail : shopThumbnails[m[1] ?? ""];
        return thumb ? png(thumb) : missing("thumbnail");
      },
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
              const last = this.versions.at(-1) ?? firstVersion(this.scenario);
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
        const from = this.version(m[1]);
        return from ? json(this.derive(from, { origin: "restore" })) : missing("version");
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
        const last = () => this.versions.at(-1) ?? firstVersion(this.scenario);
        return json(
          this.job("refine", () => this.derive(last(), { origin: "refine", prompt: instruction }), steps),
        );
      },
    ],
    ["POST", /^\/shares$/, () => json({ id: "s1", url: "/s/s1" })],
    [
      "POST",
      /^\/bugs$/,
      (_, req) => {
        this.bugs.push(req.postDataJSON() as BugReport);
        return json({ id: `b${this.bugs.length}` }, 201);
      },
    ],
    ["GET", /^\/projects\/p1\/context$/, () => json({ files: this.files, stats: this.stats() })],
    ["POST", /^\/projects\/p1\/context$/, (_, req) => json(this.upload(uploadedNames(req)), 202)],
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
    ["GET", /^\/projects\/p1\/graph$/, () => json(graphOf(this.files))],
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
    const g = graphOf(this.files);
    return {
      files: this.files.length,
      facts: 21,
      rules: 2,
      entities: g.nodes.length,
      relations: g.edges.length,
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
        const isJson = req.headers()["content-type"]?.includes("json") ?? false;
        this.requests.push({
          method: req.method(),
          path: pathname,
          body: isJson ? req.postDataJSON() : null,
          at: Date.now(),
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
