import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { asset, edgePlate } from "./fixtures";
import { MockApi } from "./mock-api";

// The agent I/O components on the harness page (e2e/harness) until the home and workspace pages mount them.
const open = (page: Page, view: "home" | "workspace", extra = "") =>
  page.goto(`/e2e/harness/agent.html?view=${view}${extra}`);

const files = [
  { name: "plate-photo.png", mimeType: "image/png", buffer: asset("plate.png") },
  { name: "old-plate.glb", mimeType: "model/gltf-binary", buffer: asset("plate.glb") },
  { name: "plate-spec.md", mimeType: "text/markdown", buffer: Buffer.from("REQ-1 Plate 120 x 80 x 6 mm\n") },
];

const noSideScroll = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

test("composer: one Attach, status to facts, one generate with every id, then the card to Open and STL", async ({
  page,
}) => {
  const api = new MockApi();
  await api.install(page);
  await open(page, "home", "&context=f3");
  const form = page.getByRole("form", { name: "New generation" });
  await expect(form.getByRole("list", { name: "Context files" })).toHaveText("plate-design-rules.md");

  await form.locator("input[type=file]").setInputFiles(files);
  const tray = form.getByRole("list", { name: "Attachments" }).getByRole("listitem");
  await expect(tray).toHaveCount(3);
  await expect(tray.filter({ hasText: "1 fact" })).toHaveCount(3);
  const box = page.getByLabel("Describe the part");
  await box.fill("Copy this plate but 120 x 80 x 6 mm with M6 holes");
  await expect(form.locator("mark")).toHaveText(["120 x 80 x 6 mm", "M6"]);
  await form.getByRole("combobox", { name: "Process" }).selectOption("fdm");
  await box.press("Control+Enter");

  const card = page.getByRole("region", { name: "Generation timeline" });
  await expect(card.getByRole("status")).toHaveText("done");
  await expect(card.locator(".step-kind")).toHaveText([
    "Requirements",
    "Model written",
    "Check",
    "Repair",
    "Done",
  ]);
  await expect(card.locator(".agent-step").nth(2)).toHaveAttribute("data-state", "fail");
  await expect(card.getByText("Repairs the failed check above")).toBeVisible();
  await expect(card.getByRole("img", { name: "done step preview" })).toBeVisible();
  await expect(card.getByRole("link", { name: "Open model" })).toHaveAttribute("href", "/m/m1");
  await expect(card.getByRole("link", { name: "Download STL" })).toHaveAttribute(
    "href",
    "/models/m1/export?fmt=stl&version=1",
  );

  const uploaded = api.files.filter((f) => files.some((a) => a.name === f.name)).map((f) => f.id);
  const generates = api.requests.filter((r) => r.path.endsWith("/generate"));
  expect(uploaded).toHaveLength(3);
  expect(generates).toHaveLength(1);
  expect(generates[0]?.body).toEqual({
    prompt: "Copy this plate but 120 x 80 x 6 mm with M6 holes",
    process: "fdm",
    attachments: uploaded,
    context_ids: ["f3"],
  });
  await expect(box).toHaveValue("");
});

test("composer: a failed upload names its reason and blocks nothing; starter cards fill the bar", async ({
  page,
}) => {
  const api = new MockApi();
  await api.install(page);
  await page.route("**/projects/p1/context", (r) =>
    r.request().method() === "POST"
      ? r.fulfill({ status: 413, json: { detail: "file too large" } })
      : r.fallback(),
  );
  await open(page, "home");
  await page.locator("input[type=file]").setInputFiles(files[2] ?? []);
  await expect(page.getByText("failed: file too large")).toBeVisible();
  await page.getByRole("button", { name: /^Spacer ring/ }).click();
  await expect(page.getByLabel("Describe the part")).toHaveValue(/^Spacer ring, 30 mm/);
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("region", { name: "Generation timeline" }).getByRole("status")).toHaveText(
    "done",
  );
  expect(api.requests.find((r) => r.path.endsWith("/generate"))?.body).toMatchObject({ attachments: [] });
});

test("workspace: refine the target, Revert, proposals, then preview, keys, compare and restore on the scrubber", async ({
  page,
}) => {
  const api = new MockApi(edgePlate);
  api.seed();
  await api.install(page);
  await open(page, "workspace", "&target");
  const history = page.getByRole("list", { name: "Version history" });
  const versions = history.locator("strong");
  await expect(versions).toHaveText(["v1"]);

  const form = page.getByRole("form", { name: "Refine" });
  await expect(form.locator(".chip")).toHaveText("Target: Sensor mounting plate");
  await page.getByLabel("Change request").fill("make it 10 mm thicker");
  await page.getByLabel("Change request").press("Enter");
  await expect(versions).toHaveText(["v2", "v1"]);
  await expect(history.locator("li").first()).toContainText("make it 10 mm thicker");
  expect(api.requests.find((r) => r.path.endsWith("/refine"))?.body).toEqual({
    instruction: "make it 10 mm thicker",
    target: "plate",
  });

  await expect(page.getByRole("status")).toHaveText(/^v2 · refine · /);
  await page.getByRole("button", { name: "Revert v2 by restoring v1 as a new version" }).click();
  await expect(versions).toHaveText(["v3", "v2", "v1"]);
  await expect(history.locator("li").first()).toContainText("restore");
  await expect(page.getByRole("button", { name: /^Revert/ })).toHaveCount(0);

  const proposals = page.getByRole("region", { name: "Suggestions" });
  await proposals.getByRole("button", { name: "Suggest changes" }).click();
  await expect(proposals.getByRole("listitem")).toHaveCount(2);
  await expect(proposals.getByRole("listitem").first()).toContainText("Hole X 20.00 → 15.00 mm");
  await proposals.getByRole("listitem").nth(1).getByRole("button", { name: "Dismiss" }).click();
  await expect(proposals.getByRole("listitem")).toHaveCount(1);
  expect(api.versions).toHaveLength(3);
  await proposals.getByRole("button", { name: "Apply" }).click();
  await expect(versions).toHaveText(["v4", "v3", "v2", "v1"]);
  await expect(history.locator("li").first()).toContainText("suggestion");
  await expect(proposals).toContainText("No open suggestions.");
  expect(api.versions.map((v) => `${v.origin} ${v.params[0]?.value}`)).toEqual([
    "generate 20",
    "refine 20",
    "restore 20",
    "suggestion 15",
  ]);

  await history.getByRole("button", { name: "v1", exact: true }).click();
  await expect(page.getByText("Viewing v1")).toBeVisible();
  await page.keyboard.press("]");
  await expect(page.getByText("Viewing v2")).toBeVisible();
  await expect(history.getByRole("button", { name: "v2", exact: true })).toBeFocused();
  await page.keyboard.press("End");
  await expect(page.getByText(/^Viewing/)).toHaveCount(0);
  expect(api.versions).toHaveLength(4);

  await page.getByRole("button", { name: "Compare" }).click();
  await history.getByRole("button", { name: "v3", exact: true }).click();
  await expect(page.getByRole("table", { name: "Parameter diff" }).getByRole("row").nth(1)).toHaveText(
    "Hole X15.0020.00 mm",
  );
  await page.getByRole("button", { name: "Compare" }).click();

  await history.getByRole("button", { name: "v3", exact: true }).click();
  await page.getByRole("button", { name: "Restore v3 as v5" }).click();
  await expect(versions).toHaveText(["v5", "v4", "v3", "v2", "v1"]);
  await expect(page.getByText(/^Viewing/)).toHaveCount(0);
  expect(api.versions.at(-1)).toMatchObject({ origin: "restore", params: [{ value: 20 }] });
});

test("every agent view fits 390 px without sideways scroll", async ({ page }) => {
  const api = new MockApi(edgePlate);
  api.seed();
  await api.install(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, "home");
  await page.locator("input[type=file]").setInputFiles(files);
  await expect(page.getByText("1 fact")).toHaveCount(3);
  expect(await noSideScroll(page)).toBe(true);
  await open(page, "workspace", "&target");
  await expect(page.getByRole("list", { name: "Version history" })).toBeVisible();
  expect(await noSideScroll(page)).toBe(true);
});

// UI_SHOTS=1 npx playwright test agent: the dark and light screenshots in docs/design/built/c.
test("screenshots", async ({ page }) => {
  test.skip(!process.env.UI_SHOTS, "set UI_SHOTS=1 to refresh docs/design/built/c");
  test.setTimeout(240_000);
  const dir = fileURLToPath(new URL("../../../docs/design/built/c/", import.meta.url));
  mkdirSync(dir, { recursive: true });
  for (const theme of ["dark", "light"])
    for (const [w, h] of [
      [1440, 900],
      [390, 844],
    ] as const) {
      await page.setViewportSize({ width: w, height: h });
      const shot = (name: string) =>
        page.screenshot({ path: `${dir}${name}-${theme}-${w}.png`, fullPage: w < 768 });

      const home = new MockApi();
      await page.unrouteAll();
      await home.install(page);
      await page.route("**/projects/p1/context", (r) =>
        r.request().method() === "POST" && r.request().postData()?.includes("scan-300dpi.pdf")
          ? r.fulfill({ status: 413, json: { detail: "file too large (52 MB, limit 50 MB)" } })
          : r.fallback(),
      );
      await open(page, "home", `&theme=${theme}&context=f3`);
      await page
        .locator("input[type=file]")
        .setInputFiles([
          ...files.slice(0, 2),
          { name: "scan-300dpi.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF") },
        ]);
      await expect(page.getByText("1 fact")).toHaveCount(2);
      await page
        .getByLabel("Describe the part")
        .fill("Sensor plate 120 x 80 x 6 mm, four M6 clearance holes, Ø20 bore");
      await shot("composer");
      await page.getByRole("button", { name: "Generate" }).click();
      await expect(page.getByRole("link", { name: "Download STL" })).toBeVisible();
      await shot("card");

      const ws = new MockApi(edgePlate);
      ws.seed();
      ws.drip = 700;
      await page.unrouteAll();
      await ws.install(page);
      await open(page, "workspace", `&theme=${theme}&target`);
      const job = await page.evaluate(() =>
        fetch("/projects/p1/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: "Edge test plate" }),
        }).then((r) => r.json() as Promise<{ id: string }>),
      );
      await open(page, "workspace", `&theme=${theme}&target&job=${job.id}`);
      await expect(page.locator(".step-kind")).toHaveCount(4, { timeout: 15_000 });
      await shot("dock");

      ws.drip = undefined;
      await expect(page.getByRole("list", { name: "Version history" }).locator("strong")).toHaveText(["v1"], {
        timeout: 15_000,
      });
      const proposals = page.getByRole("region", { name: "Suggestions" });
      await proposals.getByRole("button", { name: "Suggest changes" }).click();
      await proposals.getByRole("button", { name: "Apply" }).first().click();
      await expect(page.getByRole("button", { name: "v2", exact: true })).toBeVisible();
      await page.getByLabel("Change request").fill("move the hole 5 mm left, keep Ø10");
      await page.getByRole("button", { name: "v1", exact: true }).click();
      await page.getByRole("button", { name: "Compare" }).click();
      await page.getByRole("button", { name: "v2", exact: true }).click();
      await page.getByRole("button", { name: "v2", exact: true }).hover();
      await shot("versions");
    }
});
