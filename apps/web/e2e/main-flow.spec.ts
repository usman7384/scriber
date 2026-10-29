import { expect, test } from "@playwright/test";
import { MockApi } from "./mock-api";

test("open project, generate, watch timeline, edit a parameter, restore", async ({ page, baseURL }) => {
  const api = new MockApi();
  await api.install(page);
  const offsite: string[] = [];
  page.on(
    "request",
    (r) => r.url().startsWith(baseURL ?? "") || r.url().startsWith("data:") || offsite.push(r.url()),
  );

  await page.goto("/");
  await page.getByRole("link", { name: "Bracket lab" }).click();
  await expect(page.getByRole("heading", { name: "Bracket lab" })).toBeVisible();
  await expect(page.getByText("No models yet.")).toBeVisible();

  await page.getByRole("button", { name: /^Spacer ring/ }).click();
  await expect(page.getByLabel("Describe the part")).toHaveValue(/^Spacer ring/);
  await page.getByLabel("Describe the part").fill("Sensor plate 120 x 80 x 6 mm with four M6 holes");
  await page.getByRole("combobox").selectOption("milling_3axis");
  await page.getByRole("button", { name: "Generate" }).click();

  const timeline = page.getByRole("region", { name: "Generation timeline" });
  await expect(timeline.getByRole("status")).toHaveText("done");
  await expect(timeline.locator(".step-kind")).toHaveText([
    "requirements",
    "emit",
    "check",
    "repair",
    "done",
  ]);
  await expect(timeline.getByText("attempt 2").first()).toBeVisible();
  await expect(timeline.getByRole("img", { name: "done step preview" })).toBeVisible();
  expect(api.requests.find((r) => r.path.endsWith("/generate"))?.body).toMatchObject({
    process: "milling_3axis",
  });
  await expect(
    page.getByRole("list", { name: "Models" }).getByRole("link", { name: "Sensor plate" }),
  ).toBeVisible();

  await timeline.getByRole("link", { name: "Open model" }).click();
  await expect(page.getByRole("heading", { name: "Sensor plate" })).toBeVisible();
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 6.0 mm");
  await expect(page.getByText("L 120.0 mm")).toBeVisible();
  await page.getByRole("button", { name: "Top" }).click();
  await expect(page.getByRole("button", { name: "Top" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("list", { name: "Components" }).getByRole("button")).toHaveText([
    "Sensor mounting plate plate",
  ]);
  const marker = page.getByLabel(/^Finding: Hole Ø6.6/);
  await marker.hover();
  await expect(marker.getByRole("tooltip")).toContainText("Keep hole centres");

  await page.getByLabel("Plate Length", { exact: true }).fill("130");
  await page.getByLabel("Plate Length", { exact: true }).press("Enter");
  await expect(page.getByRole("region", { name: "Generation timeline" }).getByRole("status")).toHaveText(
    "done",
  );
  expect(api.requests.find((r) => r.method === "PATCH")?.body).toEqual({ values: { plate_length: 130 } });
  const history = page.getByRole("list", { name: "Version history" });
  await expect(history.locator("strong")).toHaveText(["v2", "v1"]);
  await expect(page.getByLabel("Plate Length", { exact: true })).toHaveValue("130");

  await history.getByRole("button", { name: "Restore v1" }).click();
  await expect(history.locator("strong")).toHaveText(["v3", "v2", "v1"]);
  await expect(history.locator("li").first()).toContainText("restore");
  await expect(page.locator(".editor-head .badge")).toHaveText("v3");
  await expect(page.getByLabel("Plate Length", { exact: true })).toHaveValue("120");

  await page.getByRole("list", { name: "Components" }).getByRole("button").click();
  await expect(page.getByText("Target: Sensor mounting plate")).toBeVisible();
  await page.getByLabel("Change request").fill("make it 10 mm thicker");
  await page.getByRole("button", { name: "Refine" }).click();
  await expect(history.locator("strong")).toHaveText(["v4", "v3", "v2", "v1"]);
  await expect(history.locator("li").first()).toContainText("make it 10 mm thicker");
  expect(api.requests.find((r) => r.path.endsWith("/refine"))?.body).toEqual({
    instruction: "make it 10 mm thicker",
    target: "plate",
  });

  await page.getByRole("button", { name: "Share" }).click();
  await expect(page.getByLabel("Share link")).toHaveValue(`${baseURL}/shared/s1`);
  expect(offsite).toEqual([]);
});
