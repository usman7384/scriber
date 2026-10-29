import { expect, test } from "@playwright/test";
import { graphOf } from "./fixtures";
import { MockApi } from "./mock-api";

test("context manager lists files, filters, deletes, and shows the graph and level", async ({ page }) => {
  const api = new MockApi();
  await api.install(page);
  await page.goto("/p/p1/context");

  const rows = page.getByRole("table", { name: "Context files" }).locator("tbody tr");
  await expect(rows).toHaveCount(6);
  await page.getByLabel("Search files").fill("motor");
  await expect(rows.locator("td:first-child")).toHaveText(["motor-mount-spec.pdf", "nema17-motor.step"]);
  await page.getByLabel("Search files").fill("");

  await page.getByRole("button", { name: "Delete notes.txt" }).click();
  await page.getByRole("button", { name: "Confirm delete" }).click();
  await expect(rows).toHaveCount(5);
  expect(api.requests.some((r) => r.method === "DELETE" && r.path.endsWith("/f4"))).toBe(true);

  await page.getByRole("button", { name: "motor-mount-spec.pdf", exact: true }).click();
  await expect(page.getByRole("region", { name: "Facts from motor-mount-spec.pdf" })).toContainText("p1:l2");

  await expect(page.getByRole("table", { name: "Project rules" })).toContainText("plate-design-rules.md:4");
  await expect(page.getByRole("heading", { name: "Knowledge base level 1" })).toBeVisible();

  const kg = page.getByRole("region", { name: "Knowledge graph" });
  const graph = graphOf(api.files);
  await expect(kg.locator("circle.node")).toHaveCount(graph.nodes.length);
  await expect(kg).toContainText(`${graph.nodes.length} entities · ${graph.edges.length} relations`);
  await kg.getByRole("button", { name: "Fullscreen" }).click();
  await expect(kg).toHaveClass(/fullscreen/);
  await kg.getByRole("button", { name: "Exit fullscreen" }).click();
  await expect(kg).not.toHaveClass(/fullscreen/);
});
