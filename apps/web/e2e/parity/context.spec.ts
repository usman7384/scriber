import { contextFiles, graphOf } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";

const columns = ["Name", "Type", "Status", "Facts", "Used in", "Uploaded", "Actions"];

test("CX-2 context file table: columns, search, select, delete from list and graph", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await api.install(page);
  await page.goto("/p/p1/context");
  const table = page.getByRole("table", { name: "Context files" });
  const rows = table.locator("tbody tr");
  const nodes = page.getByRole("region", { name: "Knowledge graph" }).locator("circle.node");

  await expect(table.locator("th")).toHaveText(columns);
  await expect(rows).toHaveCount(contextFiles.length);
  for (const [i, f] of contextFiles.entries())
    await expect(rows.nth(i).locator("td").first()).toHaveText(f.name);
  await expect(rows.first().locator("td").nth(4)).toHaveText("1 models");
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
