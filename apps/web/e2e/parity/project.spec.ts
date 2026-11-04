import { readFileSync, writeFileSync } from "node:fs";
import { asset, motorHolder, shopModels } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";
import { seenProgress, watchProgress } from "./watch";

test("WP-2 prompt card with image, mesh and spec attachments makes one generation job", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await api.install(page);
  await page.goto("/p/p1");
  const attachments = [
    { name: "plate-photo.png", mimeType: "image/png", buffer: asset("plate.png") },
    { name: "old-plate.glb", mimeType: "model/gltf-binary", buffer: asset("plate.glb") },
    {
      name: "plate-spec.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("# Plate\nREQ-1 Plate size 120 x 80 x 6 mm\n"),
    },
  ];
  const attach = page.getByRole("form", { name: "New generation" }).locator("input[type=file]").first();
  for (const file of attachments) await attach.setInputFiles(file);
  await expect(page.getByRole("list", { name: "Attachments" }).getByRole("listitem")).toHaveCount(3);
  await page.getByLabel("Describe the part").fill("Copy this plate but 120 x 80 x 6 mm");
  await row.shot("1-attached");
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("region", { name: "Generation timeline" }).getByRole("status")).toHaveText(
    "done",
  );
  await row.shot("2-generated");

  const uploaded = api.files.filter((f) => attachments.some((a) => a.name === f.name)).map((f) => f.id);
  const generates = api.requests.filter((r) => r.path.endsWith("/generate"));
  const sent = (generates[0]?.body as { attachments?: string[] } | undefined)?.attachments ?? [];
  Object.assign(row.measured, {
    uploaded_files: uploaded.length,
    generate_requests: generates.length,
    attachments_in_job: sent.join(", "),
  });
  expect(uploaded).toHaveLength(3);
  expect(generates).toHaveLength(1);
  expect(sent).toEqual(uploaded);
  row.note = "Upload, ingest and generate endpoints are mocked; the request shape follows docs/API.md.";
});

test("WP-4 example prompt chips fill the prompt box", async ({ page, row }) => {
  await new MockApi().install(page);
  await page.goto("/p/p1");
  const chips = page.getByLabel("Example prompts").getByRole("button");
  await expect(chips.first()).toBeVisible();
  const texts = await chips.allTextContents();
  let filled = 0;
  for (const [i, text] of texts.entries()) {
    await chips.nth(i).click();
    await expect(page.getByLabel("Describe the part")).toHaveValue(text);
    filled++;
  }
  Object.assign(row.measured, { chips: texts.length, filled });
  expect(texts.length).toBeGreaterThanOrEqual(4);
  await row.shot("chip-filled");
});

test("WP-5 navigation reaches every dashboard page and lists generations per project", async ({
  page,
  context,
  row,
}) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await context.route("**/docs", (r) =>
    r.fulfill({ contentType: "text/html", body: "<title>API docs</title><h1>API docs</h1>" }),
  );
  const nav = page.getByRole("navigation", { name: "Main" });
  const reached: string[] = [];
  const visit = async (name: string, path: RegExp, heading: string) => {
    await nav.getByRole("link", { name, exact: true }).click();
    await expect(page).toHaveURL(path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await row.shot(`${reached.length + 1}-${name.toLowerCase()}`);
    reached.push(name);
  };
  // Settings and Help are sheets over the current page; Esc closes them.
  const sheet = async (name: string, path: RegExp) => {
    await nav.getByRole("link", { name, exact: true }).click();
    await expect(page).toHaveURL(path);
    await expect(page.getByRole("dialog", { name })).toBeVisible();
    await row.shot(`${reached.length + 1}-${name.toLowerCase()}`);
    reached.push(name);
  };

  await page.goto("/help");
  await expect(page.getByRole("dialog", { name: "Help" })).toBeVisible();
  await page.keyboard.press("Escape");
  await visit("Projects", /\/$/, "Projects");
  await visit("All parts", /\/library$/, "All parts");
  await sheet("Settings", /\/settings$/);
  await page.getByLabel("Dark").check();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Light").check();
  await page.keyboard.press("Escape");
  await sheet("Help", /\/help$/);
  await page.keyboard.press("Escape");

  await nav.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("link", { name: "Bracket lab" }).click();
  await expect(page).toHaveURL(/\/p\/p1$/);
  const models = page.getByRole("list", { name: "Models" }).getByRole("listitem");
  // allTextContents does not wait, so a slow models reply read as an empty list
  await expect(models.first()).toBeVisible();
  const generations = await models.allTextContents();
  await row.shot(`${reached.length + 1}-project-models`);
  reached.push("Project models");
  await page.getByRole("navigation", { name: "Project" }).getByRole("link", { name: "Sources" }).click();
  await expect(page.getByRole("table", { name: "Context files" })).toBeVisible();
  await row.shot(`${reached.length + 1}-sources`);
  reached.push("Sources");
  // The Sources sheet is modal; close it before going back to the sidebar.
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/\/p\/p1$/);

  await nav.getByRole("link", { name: "Settings", exact: true }).click();
  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    page.getByRole("dialog", { name: "Settings" }).getByRole("link", { name: "API docs" }).click(),
  ]);
  await expect(popup).toHaveURL(/\/docs$/);
  reached.push("API docs");
  await popup.close();

  Object.assign(row.measured, { pages: reached.join(", "), project_generations: generations.length });
  expect(generations).toHaveLength(1);
  expect(generations[0]).toContain("Sensor plate");
  row.note = "The API docs page is served by apps/api at /docs; the test stubs it.";
});

test("WP-9 library lists every part with thumbnail and title, newest first", async ({ page, row }) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/library");
  const expected = [...api.models, ...shopModels]
    .sort((a, b) => b.created.localeCompare(a.created))
    .map((m) => m.title);
  const cards = page.getByRole("list", { name: "Models" }).getByRole("listitem");
  await expect(cards.locator(".card-title")).toHaveText(expected);
  const imgs = cards.locator("img");
  await expect
    .poll(() => imgs.evaluateAll((all: HTMLImageElement[]) => all.every((i) => i.naturalWidth > 0)))
    .toBe(true);
  Object.assign(row.measured, {
    parts: expected.length,
    projects: 2,
    order: expected.join(" > "),
    thumbnails_loaded: await imgs.count(),
  });
  await row.shot("library");
});

test("WP-6 progress bar follows the SSE progress events to 100 %", async ({ page, row }) => {
  const api = new MockApi();
  api.drip = 150;
  await api.install(page);
  await page.goto("/p/p1");
  await watchProgress(page);
  await page.getByLabel("Describe the part").fill("Sensor plate 120 x 80 x 6 mm with four M6 holes");
  await page.getByRole("button", { name: "Generate" }).click();
  const timeline = page.getByRole("region", { name: "Generation timeline" });
  await expect(timeline.getByRole("progressbar", { name: "Progress" })).toBeVisible();
  await row.shot("1-running");
  await expect(timeline.getByRole("status")).toHaveText("done");
  await row.shot("2-done");

  const sent = (api.jobs.get("generate-1")?.events ?? []).flatMap(([kind, data]) =>
    kind === "step" && "progress" in data ? [data.progress ?? 0] : [],
  );
  const shown = (await seenProgress(page)).Progress ?? [];
  Object.assign(row.measured, {
    sse_progress_events: sent.join(", "),
    bar_values_seen: shown.join(", "),
    event_spacing_ms: api.drip ?? null,
  });
  expect(sent.length).toBeGreaterThanOrEqual(3);
  expect(sent.at(-1)).toBe(100);
  expect(shown).toEqual(sent);
  row.note =
    "The mock stream sends one event per response and the browser reconnects for the next (EventSource retry), so the bar is sampled while events arrive; progress values are apps/api work.PROGRESS.";
});

// A binary STL is watertight and consistently oriented when every directed edge appears once and its reverse once.
function stlReport(stl: Buffer) {
  type V = [number, number, number];
  const count = stl.readUInt32LE(80);
  const vertex = (o: number): V => [stl.readFloatLE(o), stl.readFloatLE(o + 4), stl.readFloatLE(o + 8)];
  const edges = new Map<string, number>();
  const lo: V = [Infinity, Infinity, Infinity];
  const hi: V = [-Infinity, -Infinity, -Infinity];
  let volume = 0;
  for (let t = 0; t < count; t++) {
    const o = 84 + t * 50 + 12;
    const tri: [V, V, V] = [vertex(o), vertex(o + 12), vertex(o + 24)];
    const [a, b, c] = tri;
    volume +=
      (a[0] * (b[1] * c[2] - b[2] * c[1]) -
        a[1] * (b[0] * c[2] - b[2] * c[0]) +
        a[2] * (b[0] * c[1] - b[1] * c[0])) /
      6;
    const keys = tri.map((v) => {
      v.forEach((x, i) => {
        lo[i] = Math.min(lo[i] ?? x, x);
        hi[i] = Math.max(hi[i] ?? x, x);
      });
      return v.map((x) => x.toFixed(4)).join(",");
    });
    keys.forEach((k, i) => {
      const e = `${k}>${keys[(i + 1) % 3]}`;
      edges.set(e, (edges.get(e) ?? 0) + 1);
    });
  }
  const closed = [...edges].every(([e, n]) => n === 1 && edges.get(e.split(">").reverse().join(">")) === 1);
  return { triangles: count, size: hi.map((h, i) => h - (lo[i] ?? h)), volume, closed };
}

test("WP-14 beginner flow: prompt to STL download in three UI steps", async ({ page, row }) => {
  const api = new MockApi(motorHolder);
  await api.install(page);
  await page.goto("/p/p1");
  const steps: string[] = [];
  const prompt = "motor holder for 28 mm motor, 2 M3 screws";

  await page.getByLabel("Describe the part").fill(prompt);
  steps.push("type the prompt");
  await page.getByRole("button", { name: "Generate" }).click();
  steps.push("Generate");
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download STL" }).click();
  steps.push("Download STL");
  await row.shot("1-done");
  // Browser downloads bypass Playwright's request interception, so the bytes are fetched from the same URL through the mock.
  const file = await download;
  const fetched = await page.evaluate(async (url) => {
    const res = await fetch(url);
    const bytes = new Uint8Array(await res.arrayBuffer());
    const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? "model.stl";
    return { name, b64: btoa(Array.from(bytes, (b) => String.fromCharCode(b)).join("")) };
  }, file.url());
  const path = `${row.dir}/${fetched.name}`;
  writeFileSync(path, Buffer.from(fetched.b64, "base64"));

  const stl = stlReport(readFileSync(path));
  const generate = api.requests.find((r) => r.path.endsWith("/generate"))?.body as { prompt: string };
  Object.assign(row.measured, {
    ui_steps: steps.length,
    steps: steps.join(" -> "),
    prompt_sent: generate.prompt,
    download_url: new URL(file.url()).pathname + new URL(file.url()).search,
    stl_file: fetched.name,
    triangles: stl.triangles,
    size_mm: stl.size.map((v) => +v.toFixed(3)).join(" x "),
    volume_mm3: +stl.volume.toFixed(1),
    watertight_and_oriented: stl.closed,
  });
  expect(steps).toHaveLength(3);
  expect(generate.prompt).toBe(prompt);
  expect(stl.closed).toBe(true);
  expect(stl.size.map((v) => +v.toFixed(2))).toEqual(motorHolder.metrics.bbox);
  expect(Math.abs(stl.volume - motorHolder.metrics.volume) / motorHolder.metrics.volume).toBeLessThan(0.01);
  row.note =
    "STL is geometry-service output for a hand-written motor-holder IR standing in for the model's answer (generation is mocked). VM-9 needs a slicer run on it; here it is checked watertight and consistently oriented.";
});
