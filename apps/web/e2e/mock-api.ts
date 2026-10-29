import type { Page, Request, Route } from "@playwright/test";
import type { BugReport, ContextFile, Job, Model, Step, Suggestion, Vec3, Version } from "../src/api";
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

const apiPath = /^\/(projects|models|jobs|shares|s|bugs)(\/|$)/;

type Reply = Parameters<Route["fulfill"]>[0];
type Handler = (m: RegExpMatchArray, req: Request) => Reply;
type Event = [string, Step | Job];

const json = (body: unknown, status = 200): Reply => ({ status, json: body });
const png = (body: Buffer): Reply => ({ status: 200, contentType: "image/png", body });
const missing = (what: string) => json({ detail: `no ${what}` }, 404);

// Events carry ids like apps/api. With drip set, each response holds the next event and asks the
// browser to reconnect after drip ms, so the client sees them arrive over time. Chromium's request
// interception does not show Last-Event-ID, so the mock keeps the position per job instead.
const sse = (events: Event[], after: number, drip?: number): Reply => ({
  status: 200,
  headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  body:
    (drip ? `retry: ${drip}\n\n` : "") +
    events
      .slice(after + 1, drip ? after + 2 : undefined)
      .map(([kind, data], i) => `id: ${after + 1 + i}\nevent: ${kind}\ndata: ${JSON.stringify(data)}\n\n`)
      .join(""),
});

// apps/api work.PROGRESS
const progress: Record<string, number> = { requirements: 10, emit: 40, check: 60, repair: 70, done: 100 };

const uploadedNames = (req: Request) =>
  [...(req.postDataBuffer()?.toString("latin1") ?? "").matchAll(/filename="([^"]+)"/g)].map(
    (m) => m[1] ?? "",
  );

export class MockApi {
  models: Model[] = [];
  versions: Version[] = [];
  files = [...contextFiles];
  bugs: BugReport[] = [];
  suggestions: Suggestion[] = [];
  shares = new Map<string, number>();
  requests: { method: string; path: string; body: unknown; at: number }[] = [];
  drip?: number;
  jobs = new Map<string, { run: () => Event[]; events?: Event[]; sent: number }>();

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
    this.jobs.set(id, {
      sent: -1,
      run: () => {
        const v = run();
        const done = { ...base, status: "done" as const, model_id: "m1", version: v?.number ?? null, steps };
        return [...steps.map((s): Event => ["step", s]), ["done", done]];
      },
    });
    return base;
  }

  private events(id: string) {
    const job = this.jobs.get(id);
    if (!job) return missing("job");
    job.events ??= job.run();
    const after = this.drip ? job.sent++ : -1;
    return sse(job.events, after, this.drip);
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
    const built = this.build(v);
    return this.addVersion({ ...v, findings: built?.findings ?? [], metrics: built?.metrics ?? v.metrics });
  }

  private version(n: string | null | undefined) {
    return this.versions.find((v) => v.number === Number(n));
  }

  private rebuild(origin: Version["origin"], values: Record<string, number>) {
    const steps: Step[] = [
      { kind: "done", message: "rebuilt without the LLM", attempt: 0, elapsed_ms: 640, progress: 100 },
    ];
    const run = () => {
      const last = this.versions.at(-1) ?? firstVersion(this.scenario);
      const params = last.params.map((p) => ({ ...p, value: values[p.name] ?? p.value }));
      return this.derive(last, { origin, params });
    };
    return this.job("params", run, steps);
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
    return added.map((f) =>
      this.job("ingest", () => undefined, [
        { kind: "ingest", message: `reading ${f.name}`, attempt: 1, elapsed_ms: 0, progress: 0 },
        {
          kind: "ingest",
          message: `${f.name}: ${f.kind}, 1 facts`,
          attempt: 1,
          elapsed_ms: 120,
          progress: 100,
        },
      ]),
    );
  }

  private generate(req: Request) {
    const { context_ids } = req.postDataJSON() as { context_ids?: string[] };
    const steps: Step[] = [
      { kind: "requirements", message: "REQ-1 Plate size 120 x 80 x 6 mm", attempt: 0, elapsed_ms: 500 },
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
    ];
    const run = () => {
      this.files = this.files.map((f) =>
        context_ids?.includes(f.id) && !f.used_in.includes("m1")
          ? { ...f, used_in: [...f.used_in, "m1"] }
          : f,
      );
      return this.seed();
    };
    return json(
      this.job(
        "generate",
        run,
        steps.map((s) => ({ ...s, progress: progress[s.kind] ?? 0 })),
      ),
    );
  }

  private settle(id: string | undefined, status: Suggestion["status"]) {
    const found = this.suggestions.find((s) => s.id === id);
    if (!found) return { error: missing("suggestion") };
    if (found.status !== "open")
      return { error: json({ detail: `suggestion ${id} is already ${found.status}` }, 409) };
    const settled = { ...found, status };
    this.suggestions = this.suggestions.map((s) => (s === found ? settled : s));
    return { settled };
  }

  private shared(id: string | undefined) {
    const v = this.version(String(this.shares.get(id ?? "")));
    return v && { v, built: this.build(v) };
  }

  private routes: [string, RegExp, Handler][] = [
    ["GET", /^\/projects$/, () => json([{ ...project, model_count: this.models.length }, shop])],
    ["GET", /^\/projects\/p1$/, () => json(project)],
    ["GET", /^\/projects\/p2$/, () => json(shop)],
    ["GET", /^\/projects\/p1\/models$/, () => json(this.models)],
    ["GET", /^\/projects\/p2\/models$/, () => json(shopModels)],
    ["GET", /^\/projects\/p\d\/jobs$/, () => json([])],
    ["POST", /^\/projects\/p1\/generate$/, (_, req) => this.generate(req)],
    ["GET", /^\/jobs\/([\w-]+)\/events$/, (m) => this.events(m[1] ?? "")],
    ["GET", /^\/models\/m1$/, () => json(this.models[0])],
    ["GET", /^\/models\/m1\/versions$/, () => json(this.versions)],
    [
      "GET",
      /^\/models\/m1\/export$/,
      (_, req) => {
        const query = new URL(req.url()).searchParams;
        const n = query.get("version");
        const built = this.build(this.version(n));
        const fmt = query.get("fmt");
        const body = fmt === "stl" ? built?.stl : fmt === "glb" ? built?.glb : undefined;
        if (!body) return missing("geometry");
        // Same name and media type as apps/api routes/common.export
        const name = `${this.scenario.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-v${n}.${fmt}`;
        return {
          status: 200,
          contentType: fmt === "stl" ? "model/stl" : "model/gltf-binary",
          headers: { "Content-Disposition": `attachment; filename="${name}"` },
          body,
        };
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
      "GET",
      /^\/models\/m1\/components$/,
      (_, req) =>
        this.version(new URL(req.url()).searchParams.get("version"))
          ? json(this.scenario.components)
          : missing("version"),
    ],
    [
      "POST",
      /^\/models\/m1\/face-driver$/,
      (_, req) => {
        const pick = req.postDataJSON() as { point: Vec3; normal: Vec3; version: number };
        const v = this.version(String(pick.version));
        const found = v && this.scenario.faceDriver?.(pick.point, pick.normal, valuesOf(v.params));
        return found ? json(found) : json({ detail: "no parameter drives this face" }, 404);
      },
    ],
    [
      "PATCH",
      /^\/models\/m1\/params$/,
      (_, req) =>
        json(this.rebuild("params", (req.postDataJSON() as { values: Record<string, number> }).values)),
    ],
    ["GET", /^\/models\/m1\/suggestions$/, () => json(this.suggestions)],
    [
      "POST",
      /^\/models\/m1\/suggestions$/,
      () => json((this.suggestions = [...(this.scenario.suggestions ?? [])]), 201),
    ],
    [
      "POST",
      /^\/models\/m1\/suggestions\/(\w+)\/accept$/,
      (m) => {
        const { settled, error } = this.settle(m[1], "accepted");
        return error ?? json(this.rebuild("suggestion", settled?.change ?? {}), 202);
      },
    ],
    [
      "POST",
      /^\/models\/m1\/suggestions\/(\w+)\/ignore$/,
      (m) => {
        const { settled, error } = this.settle(m[1], "ignored");
        return error ?? json(settled);
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
          { kind: "done", message: "1 parameter changed", attempt: 1, elapsed_ms: 9100, progress: 100 },
        ];
        const last = () => this.versions.at(-1) ?? firstVersion(this.scenario);
        return json(
          this.job("refine", () => this.derive(last(), { origin: "refine", prompt: instruction }), steps),
        );
      },
    ],
    [
      "POST",
      /^\/shares$/,
      (_, req) => {
        const id = `s${this.shares.size + 1}`;
        this.shares.set(id, (req.postDataJSON() as { version: number }).version);
        return json({ id, url: `/s/${id}` }, 201);
      },
    ],
    [
      "DELETE",
      /^\/shares\/(\w+)$/,
      (m) => (this.shares.delete(m[1] ?? "") ? { status: 204 } : missing("share")),
    ],
    [
      "GET",
      /^\/s\/(\w+)$/,
      (m) => {
        const found = this.shared(m[1]);
        if (!found) return json({ detail: "share link not found or revoked" }, 404);
        const url = (kind: string) => `/s/${m[1]}/files/${kind}`;
        const files = Object.fromEntries(["step", "stl", "glb", "py", "ir"].map((k) => [k, url(k)]));
        const version = { ...found.v, files, thumbnail_url: url("thumbnail") };
        return json({ ...this.models[0], thumbnail_url: url("thumbnail"), version });
      },
    ],
    [
      "GET",
      /^\/s\/(\w+)\/files\/(\w+)$/,
      (m) => {
        const built = this.shared(m[1])?.built;
        if (m[2] === "thumbnail" && built) return png(built.thumbnail);
        if (m[2] === "glb" && built)
          return { status: 200, contentType: "model/gltf-binary", body: built.glb };
        return json({ detail: "share link not found or revoked" }, 404);
      },
    ],
    [
      "POST",
      /^\/bugs$/,
      (_, req) => {
        this.bugs.push(req.postDataJSON() as BugReport);
        return json({ id: `b${this.bugs.length}` }, 201);
      },
    ],
    ["GET", /^\/projects\/p1\/context$/, () => json({ files: this.files, stats: this.stats(), stale: [] })],
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

  // Counts as services/context store.counts does; score and level by the documented formula (LocalContext.stats).
  stats() {
    const g = graphOf(this.files);
    const sum = (key: "facts" | "rules") => this.files.reduce((n, f) => n + f[key], 0);
    const counts = {
      files: this.files.length,
      facts: sum("facts"),
      rules: sum("rules"),
      entities: g.nodes.length,
      relations: g.edges.length,
      generations: this.versions.length,
      used_in_generation: this.files.filter((f) => f.used_in.length > 0).length,
    };
    const score = 10 * counts.files + 2 * counts.facts + 5 * counts.rules + 20 * counts.used_in_generation;
    const level = Math.floor(Math.sqrt(Math.floor(score / 100)));
    return { ...counts, score, level, next_level_score: 100 * (level + 1) ** 2 };
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
