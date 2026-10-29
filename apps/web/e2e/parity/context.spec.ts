import type { Page } from "@playwright/test";
import { asset, contextFiles, graphOf } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";
import { seenProgress, watchProgress } from "./watch";

const columns = ["Name", "Type", "Status", "Facts", "Used in", "Uploaded", "Actions"];

test("CX-2 context file table: columns, search, select, delete from list and graph", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/p/p1/context");
  const table = page.getByRole("table", { name: "Context files" });
  const rows = table.locator("tbody tr");
  const nodes = page.getByRole("region", { name: "Knowledge graph" }).locator("circle.node");

  await expect(table.locator("th")).toHaveText(columns);
  await expect(rows).toHaveCount(contextFiles.length);
  for (const [i, f] of contextFiles.entries())
    await expect(rows.nth(i).locator("td").first()).toHaveText(f.name);
  await expect(rows.first().locator("td").nth(4)).toHaveText("Sensor plate");
  await row.shot("1-table");

  await page.getByLabel("Search files").fill("motor");
  const matches = await rows.locator("td:first-child").allTextContents();
  expect(matches).toEqual(["motor-mount-spec.pdf", "nema17-motor.step"]);
  await row.shot("2-search");
  await page.getByLabel("Search files").fill("");

  await page.getByRole("button", { name: "hole-table.csv", exact: true }).click();
  await expect(rows.nth(4)).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("region", { name: "Facts from hole-table.csv" })).toBeVisible();

  const nodesBefore = await nodes.count();
  await page.getByRole("button", { name: "Delete notes.txt" }).click();
  await page.getByRole("button", { name: "Confirm delete" }).click();
  await expect(rows).toHaveCount(contextFiles.length - 1);
  await expect(nodes).toHaveCount(nodesBefore - 1);
  const titles = await nodes.locator("title").allTextContents();
  await row.shot("3-deleted");

  Object.assign(row.measured, {
    columns: columns.join(", "),
    rows: contextFiles.length,
    search_motor: matches.join(", "),
    rows_after_delete: await rows.count(),
    graph_nodes_before: nodesBefore,
    graph_nodes_after: titles.length,
    deleted_file_in_graph: titles.includes("file: notes.txt"),
  });
  expect(titles).not.toContain("file: notes.txt");
  expect(api.requests.some((r) => r.method === "DELETE" && r.path.endsWith("/f4"))).toBe(true);
  row.note =
    "Graph removal is mocked like services/context does it (test_delete_document_removes_its_records).";
});

test("CX-5 knowledge graph: node count and counters match the API, fullscreen toggles", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await api.install(page);
  await page.goto("/p/p1/context");
  const { counts } = graphOf(api.files);
  const kg = page.getByRole("region", { name: "Knowledge graph" });
  await expect(kg.locator("circle.node")).toHaveCount(counts.entities ?? -1);
  await expect(kg.locator("line.edge")).toHaveCount(counts.relations ?? -1);
  const counter = `${counts.entities} entities · ${counts.relations} relations`;
  await expect(kg).toContainText(counter);
  await row.shot("1-graph");

  await kg.getByRole("button", { name: "Fullscreen" }).click();
  await expect(kg).toHaveClass(/fullscreen/);
  const full = await kg.boundingBox();
  const viewport = page.viewportSize();
  await row.shot("2-fullscreen");
  await kg.press("Escape");
  await expect(kg).not.toHaveClass(/fullscreen/);
  await kg.getByRole("button", { name: "Fullscreen" }).click();
  await kg.getByRole("button", { name: "Exit fullscreen" }).click();
  await expect(kg).not.toHaveClass(/fullscreen/);
  await row.shot("3-exited");

  Object.assign(row.measured, {
    api_entities: counts.entities ?? null,
    api_relations: counts.relations ?? null,
    rendered_nodes: await kg.locator("circle.node").count(),
    counter,
    fullscreen_px: full ? `${Math.round(full.width)} x ${Math.round(full.height)}` : null,
    viewport_px: viewport ? `${viewport.width} x ${viewport.height}` : null,
    exits: "Escape and button",
  });
  expect(full?.width ?? 0).toBeGreaterThan((viewport?.width ?? 0) * 0.9);
  expect(full?.height ?? 0).toBeGreaterThan((viewport?.height ?? 0) * 0.9);
});

const sixFiles = [
  { name: "bracket-spec.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\n% spec\n") },
  { name: "motor.step", mimeType: "model/step", buffer: Buffer.from("ISO-10303-21;\nEND-ISO-10303-21;\n") },
  { name: "rules.md", mimeType: "text/markdown", buffer: Buffer.from("# Rules\nHole edge 2 x D\n") },
  { name: "notes-2.txt", mimeType: "text/plain", buffer: Buffer.from("Wall 3 mm\n") },
  { name: "holes.csv", mimeType: "text/csv", buffer: Buffer.from("x,y,d\n10,10,6.6\n") },
  { name: "photo.png", mimeType: "image/png", buffer: asset("plate.png") },
];

test("CX-1 multi-file upload shows per-file progress from 0 to 100", async ({ page, row }) => {
  const api = new MockApi();
  api.drip = 100;
  await api.install(page);
  await page.goto("/p/p1/context");
  await watchProgress(page);
  await page.locator(".dropzone input[type=file]").setInputFiles(sixFiles);
  const uploads = page.getByRole("list", { name: "Uploads" }).getByRole("listitem");
  await expect(uploads).toHaveCount(6);
  await row.shot("1-uploading");
  await expect(uploads.filter({ hasText: "processed" })).toHaveCount(6);
  await row.shot("2-processed");

  const seen = await seenProgress(page);
  const listed = await page.evaluate(() =>
    fetch("/projects/p1/context").then(
      (r) => r.json() as Promise<{ files: { name: string; status: string }[] }>,
    ),
  );
  const mine = listed.files.filter((f) => sixFiles.some((s) => s.name === f.name));
  for (const f of sixFiles) row.measured[f.name] = (seen[`${f.name} progress`] ?? []).join(" -> ");
  Object.assign(row.measured, {
    upload_requests: api.requests.filter((r) => r.method === "POST" && r.path.endsWith("/context")).length,
    listed_processed: mine.filter((f) => f.status === "processed").length,
  });
  for (const f of sixFiles) expect(seen[`${f.name} progress`]).toEqual([0, 100]);
  expect(mine.map((f) => f.status)).toEqual(Array(6).fill("processed"));
  row.note =
    "One multipart upload, one ingest job per file; each job streams progress 0 then 100 as apps/api ingest.py emits it (mocked, one event per response).";
});

async function generateWithContext(page: Page, names: string[]) {
  await page.goto("/p/p1/context");
  for (const name of names) await page.getByLabel(`Use ${name} as context`).check();
  await page.getByRole("button", { name: `Use selected as context (${names.length})` }).click();
  await expect(page.getByRole("list", { name: "Context files" }).getByRole("listitem")).toHaveCount(
    names.length + 1,
  );
  await page.getByLabel("Describe the part").fill("Sensor plate 120 x 80 x 6 mm with four M6 holes");
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("region", { name: "Generation timeline" }).getByRole("status")).toHaveText(
    "done",
  );
}

const usedIn = (page: Page, name: string) =>
  page.getByRole("table", { name: "Context files" }).locator("tr", { hasText: name }).locator("td").nth(4);

test("CX-3 selected files as context: the generation carries exactly them and they show it in Used in", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await api.install(page);
  const chosen = ["nema17-motor.step", "plate-design-rules.md"];
  const ids = chosen.map((n) => contextFiles.find((f) => f.name === n)?.id);
  await page.goto("/p/p1/context");
  for (const name of chosen) await expect(usedIn(page, name)).toHaveText("—");
  await generateWithContext(page, chosen);
  await row.shot("1-generated-with-context");
  const body = api.requests.find((r) => r.path.endsWith("/generate"))?.body as { context_ids?: string[] };

  await page.getByRole("navigation", { name: "Project" }).getByRole("link", { name: "Context" }).click();
  for (const name of chosen) await expect(usedIn(page, name)).toHaveText("Sensor plate");
  await expect(usedIn(page, "notes.txt")).toHaveText("—");
  await row.shot("2-used-in");
  Object.assign(row.measured, {
    chosen: chosen.join(", "),
    context_ids_sent: (body.context_ids ?? []).join(", "),
    used_in_after: chosen.map((n) => `${n}: Sensor plate`).join("; "),
    unchosen_used_in: "notes.txt: —",
  });
  expect(body.context_ids).toEqual(ids);
  await usedIn(page, chosen[0] ?? "")
    .getByRole("link")
    .click();
  await expect(page).toHaveURL(/\/m\/m1$/);
  row.note =
    "Web half: the generate request carries exactly the chosen ids and Used in links the new model. Recording them on the generation is apps/api (mocked here).";
});

test("CX-6 knowledge-base level and score follow the formula after uploads and a generation", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await api.install(page);
  const card = page.getByRole("region", { name: "Knowledge base" });
  const read = async (): Promise<Record<string, number>> => {
    const terms = await card.locator("dt").allTextContents();
    const values = (await card.locator("dd").allTextContents()).map(Number);
    const head = (await card.locator("header").textContent()) ?? "";
    const [, level, score, next] = /(\d+)\D+(\d+) \/ (\d+)/.exec(head) ?? [];
    return {
      ...Object.fromEntries(terms.map((t, i) => [t, values[i] ?? NaN])),
      level: Number(level),
      score: Number(score),
      next: Number(next),
    };
  };
  const expected = () => {
    const s = api.stats();
    const score = 10 * s.files + 2 * s.facts + 5 * s.rules + 20 * s.used_in_generation;
    const level = Math.floor(Math.sqrt(Math.floor(score / 100)));
    return { score, level, next: 100 * (level + 1) ** 2, s };
  };
  const check = async (stage: string) => {
    const shown = await read();
    const want = expected();
    row.measured[`${stage}_ui`] =
      `files ${shown.Files}, facts ${shown.Facts}, rules ${shown.Rules}, used ${shown["Used in generation"]}, score ${shown.score}/${shown.next}, level ${shown.level}`;
    row.measured[`${stage}_formula`] = `score ${want.score}/${want.next}, level ${want.level}`;
    expect(shown).toMatchObject({
      Files: want.s.files,
      Facts: want.s.facts,
      Rules: want.s.rules,
      "Used in generation": want.s.used_in_generation,
      score: want.score,
      level: want.level,
      next: want.next,
    });
    return shown;
  };

  await page.goto("/p/p1/context");
  await expect(card).toBeVisible();
  const before = await check("before");
  await row.shot("1-before");

  await page.locator(".dropzone input[type=file]").setInputFiles(sixFiles.slice(0, 2));
  await expect(page.getByRole("list", { name: "Uploads" }).getByText("processed")).toHaveCount(2);
  await generateWithContext(page, ["notes.txt"]);
  await page.getByRole("navigation", { name: "Project" }).getByRole("link", { name: "Context" }).click();
  await expect(card.locator("dd").nth(0)).toHaveText(String((before.Files ?? 0) + 2));
  const after = await check("after_2_uploads_1_generation");
  await row.shot("2-after");
  const delta = (after.score ?? 0) - (before.score ?? 0);
  row.measured.score_delta = delta;
  expect(delta).toBe(10 * 2 + 2 * 2 + 20 * 1);
  row.note =
    "Score = 10 files + 2 facts + 5 rules + 20 used-in-generation, level = isqrt(score / 100) (services/context LocalContext.stats); the counts come from the mocked GET /projects/{id}/context.";
});
