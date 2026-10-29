import type { APIRequestContext } from "@playwright/test";
import type { ContextFile, GraphView, Job, KbStats } from "../../src/api";
import { expect, test } from "../parity/row";
import { seenProgress, watchProgress } from "../parity/watch";
import { basePlate } from "./designs";
import { API, build, getJson, project, repoFile, upload, type Upload } from "./live";

const m3 = (name: string, as: string, mimeType: string): Upload => ({
  name: as,
  mimeType,
  buffer: repoFile(`evals/parity/m3/${name}`),
});

// Real files of six kinds; two names contain "motor" for the CX-2 search. The STEP is exported by the live API.
async function sixFiles(request: APIRequestContext, projectId: string): Promise<Upload[]> {
  const model = await build(request, projectId, basePlate);
  const step = await (await request.get(`${API}/models/${model}/export?fmt=step`)).body();
  return [
    m3("bracket_spec.pdf", "motor-bracket-spec.pdf", "application/pdf"),
    { name: "motor-plate.step", mimeType: "model/step", buffer: step },
    m3("plate_spec.md", "plate_spec.md", "text/markdown"),
    m3("notes.txt", "notes.txt", "text/plain"),
    m3("holes.csv", "holes.csv", "text/csv"),
    m3("sketch.png", "sketch.png", "image/png"),
  ];
}

const listing = (request: APIRequestContext, id: string) =>
  getJson<{ files: ContextFile[]; stats: KbStats }>(request, `/projects/${id}/context`);

test("CX-1 live: six real files in one upload, per-file progress 0 to 100, all processed", async ({
  page,
  request,
  row,
}) => {
  const id = await project(request, "CX-1 live");
  const files = await sixFiles(request, id);
  await page.goto(`/p/${id}/context`);
  await watchProgress(page);
  await page.locator(".dropzone input[type=file]").setInputFiles(files);
  const uploads = page.getByRole("list", { name: "Uploads" }).getByRole("listitem");
  await expect(uploads).toHaveCount(6);
  await row.shot("1-uploading");
  await expect(uploads.filter({ hasText: "processed" })).toHaveCount(6);
  await row.shot("2-processed");

  const seen = await seenProgress(page);
  const listed = (await listing(request, id)).files;
  for (const f of files) row.measured[f.name] = (seen[`${f.name} progress`] ?? []).join(" -> ");
  Object.assign(row.measured, {
    kinds: listed.map((f) => f.kind).join(", "),
    listed: listed.length,
    listed_processed: listed.filter((f) => f.status === "processed").length,
    facts: listed.map((f) => `${f.name} ${f.facts}`).join(", "),
  });
  expect(listed.map((f) => f.status)).toEqual(Array(6).fill("processed"));
  for (const f of files) expect(seen[`${f.name} progress`]).toEqual([0, 100]);
  row.note =
    "Live: apps/api ingest with the configured embedder, real PDF/MD/TXT/CSV/PNG fixtures and a STEP exported by the same API; progress sampled from the UI each frame.";
});

const columns = ["Name", "Type", "Status", "Facts", "Used in", "Uploaded", "Actions"];

test("CX-2 live: file table, search, select, delete removes the file from the list and the knowledge graph", async ({
  page,
  request,
  row,
}) => {
  const id = await project(request, "CX-2 live");
  const files = await sixFiles(request, id);
  await upload(request, id, files);
  const graphBefore = await getJson<GraphView>(request, `/projects/${id}/graph`);
  await page.goto(`/p/${id}/context`);
  const table = page.getByRole("table", { name: "Context files" });
  const rows = table.locator("tbody tr");
  const nodes = page.getByRole("region", { name: "Knowledge graph" }).locator("circle.node");

  await expect(table.locator("th")).toHaveText(columns);
  await expect(rows).toHaveCount(6);
  await expect(nodes).toHaveCount(graphBefore.nodes.length);
  await row.shot("1-table");

  await page.getByLabel("Search files").fill("motor");
  await expect(rows).toHaveCount(2);
  const matches = await rows.locator("td:first-child").allTextContents();
  await row.shot("2-search");
  await page.getByLabel("Search files").fill("");

  await page.getByRole("button", { name: "holes.csv", exact: true }).click();
  const facts = page.getByRole("region", { name: "Facts from holes.csv" });
  await expect(facts).toBeVisible();
  await expect(facts.getByRole("listitem").first()).toBeVisible();
  const factCount = await facts.getByRole("listitem").count();

  const doomed = "notes.txt";
  const nodesBefore = await nodes.count();
  await page.getByRole("button", { name: `Delete ${doomed}` }).click();
  await page.getByRole("button", { name: "Confirm delete" }).click();
  await expect(rows).toHaveCount(5);
  const graphAfter = await getJson<GraphView>(request, `/projects/${id}/graph`);
  await expect(nodes).toHaveCount(graphAfter.nodes.length);
  const titles = await nodes.locator("title").allTextContents();
  await row.shot("3-deleted");

  const docOf = (g: GraphView) => g.nodes.find((n) => n.type === "document" && n.name === doomed)?.id;
  const doc = docOf(graphBefore) ?? "-";
  const owned = (g: GraphView) => g.nodes.filter((n) => n.id === doc || n.id.startsWith(`${doc}:`)).length;
  const listed = (await listing(request, id)).files.map((f) => f.name);
  Object.assign(row.measured, {
    columns: columns.join(", "),
    rows: 6,
    search_motor: matches.join(", "),
    facts_shown_for_holes_csv: factCount,
    rows_after_delete: await rows.count(),
    api_files_after_delete: listed.length,
    graph_nodes_before: nodesBefore,
    graph_nodes_after: titles.length,
    api_nodes_of_deleted_file_before: owned(graphBefore),
    api_nodes_of_deleted_file_after: owned(graphAfter),
    ui_nodes_naming_deleted_file: titles.filter((t) => t.includes(doomed)).length,
  });
  expect(matches).toEqual(["motor-bracket-spec.pdf", "motor-plate.step"]);
  expect(factCount).toBeGreaterThan(0);
  expect(listed).not.toContain(doomed);
  expect(owned(graphBefore)).toBeGreaterThan(0);
  expect(owned(graphAfter)).toBe(0);
  expect(titles.filter((t) => t.includes(doomed))).toEqual([]);
  row.note =
    "Live: DELETE /projects/{id}/context/{file} through the UI; the graph is read back from apps/api (document, fact and chunk nodes of the file).";
});

test("CX-6 live: knowledge-base level and score equal the API and the formula after uploads and a generation", async ({
  page,
  request,
  row,
}) => {
  const id = await project(request, "CX-6 live");
  const card = page.getByRole("region", { name: "Knowledge base" });
  const read = async (): Promise<Record<string, number>> => {
    const terms = await card.locator("dt").allTextContents();
    const values = (await card.locator("dd").allTextContents()).map(Number);
    const [, level, score, next] =
      /(\d+)\D+(\d+) \/ (\d+)/.exec((await card.locator("header").textContent()) ?? "") ?? [];
    return {
      ...Object.fromEntries(terms.map((t, i) => [t, values[i]])),
      level: +(level ?? NaN),
      score: +(score ?? NaN),
      next: +(next ?? NaN),
    };
  };
  const check = async (stage: string) => {
    await page.goto(`/p/${id}/context`);
    await expect(card).toBeVisible();
    const s = (await listing(request, id)).stats;
    const score = 10 * s.files + 2 * s.facts + 5 * s.rules + 20 * s.used_in_generation;
    const level = Math.floor(Math.sqrt(Math.floor(score / 100)));
    const shown = await read();
    row.measured[`${stage}_api`] =
      `files ${s.files}, facts ${s.facts}, rules ${s.rules}, generations ${s.generations}, used ${s.used_in_generation}, score ${s.score}/${s.next_level_score}, level ${s.level}`;
    row.measured[`${stage}_ui`] =
      `files ${shown.files}, facts ${shown.facts}, rules ${shown.rules}, used ${shown.used}, score ${shown.score}/${shown.next}, level ${shown.level}`;
    row.measured[`${stage}_formula`] = `score ${score}/${100 * (level + 1) ** 2}, level ${level}`;
    expect([s.score, s.level, s.next_level_score]).toEqual([score, level, 100 * (level + 1) ** 2]);
    expect(shown).toMatchObject({
      files: s.files,
      facts: s.facts,
      rules: s.rules,
      used: s.used_in_generation,
      score: s.score,
      level: s.level,
      next: s.next_level_score,
    });
    await row.shot(stage);
    return s;
  };

  await check("1-empty");
  const spec = {
    name: "plate_spec.md",
    mimeType: "text/markdown",
    buffer: repoFile("evals/parity/m3/plate_spec.md"),
  };
  const notes = { name: "notes.txt", mimeType: "text/plain", buffer: repoFile("evals/parity/m3/notes.txt") };
  await page.locator(".dropzone input[type=file]").setInputFiles([spec, notes]);
  await expect(page.getByRole("list", { name: "Uploads" }).getByText("processed")).toHaveCount(2);
  const uploaded = await check("2-after-2-uploads");

  await page.getByLabel("Use plate_spec.md as context").check();
  await page.getByRole("button", { name: "Use 1 in the next generation" }).click();
  await page
    .getByLabel("Describe the part")
    .fill("mounting plate per the selected spec, 150 x 90 x 6 mm with four M6 clearance holes");
  await page.getByRole("button", { name: "Generate" }).click();
  const status = page.getByRole("region", { name: "Generation timeline" }).getByRole("status");
  await expect(status).toHaveText(/done|failed/, { timeout: 480_000 });
  row.measured.generation = (await status.textContent()) ?? "";
  const [job] = await getJson<Job[]>(request, `/projects/${id}/jobs`);
  row.measured.generation_steps = (job?.steps ?? [])
    .map((s) => `${s.kind} ${s.attempt}: ${s.message}`)
    .join(" | ");
  const generated = await check("3-after-1-generation");

  Object.assign(row.measured, {
    score_delta: generated.score - uploaded.score,
    used_delta: generated.used_in_generation - uploaded.used_in_generation,
  });
  expect(row.measured.generation).toBe("done");
  expect(uploaded.files).toBe(2);
  expect(generated.generations).toBe(1);
  row.note =
    "Live: two uploads and one model generation (default model) with plate_spec.md selected; the card is compared with GET /projects/{id}/context stats and with score = 10 files + 2 facts + 5 rules + 20 used, level = isqrt(score / 100).";
});
