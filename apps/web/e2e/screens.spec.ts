import { expect, test, type Page } from "@playwright/test";
import { basePlate, sensorPlate, type Scenario } from "./fixtures";
import { MockApi } from "./mock-api";

// SHOTS=dir npx playwright test screens: the integrated app's screens, dark and light, desktop and phone.
const sizes = [
  ["1440", { width: 1440, height: 900 }],
  ["390", { width: 390, height: 844 }],
] as const;

type Shot = (page: Page, api: MockApi, phone: boolean) => Promise<void>;

const tab = async (page: Page, phone: boolean, name: string) => {
  if (phone) await page.getByRole("tab", { name }).click();
};

const editor = async (page: Page) => {
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toHaveText(/ mm$/);
};

const screens: [string, Shot, Scenario?][] = [
  [
    "home",
    async (page) => {
      await page.goto("/p/p1");
      await expect(page.getByRole("list", { name: "Models" }).locator("img").first()).toBeVisible();
    },
  ],
  [
    "sources",
    async (page) => {
      await page.goto("/p/p1/context");
      await expect(page.getByRole("table", { name: "Context files" })).toBeVisible();
      await page.getByLabel("Use plate-design-rules.md as context").check();
    },
  ],
  [
    "workspace-face",
    async (page, _api, phone) => {
      await editor(page);
      await page.getByRole("button", { name: "Iso", exact: true }).click();
      await page.getByRole("button", { name: "Select face" }).click();
      await page.waitForTimeout(400);
      const free = await page.locator(".ws-free").boundingBox();
      if (!free) throw new Error("no free frame");
      await page.mouse.click(free.x + free.width / 2, free.y + free.height * (phone ? 0.5 : 0.45));
      await expect(page.getByLabel(/driving dimension$/)).toBeVisible();
    },
    basePlate,
  ],
  [
    "palette",
    async (page) => {
      await editor(page);
      await page.keyboard.press("Control+k");
      await page
        .getByRole("combobox", { name: "Search actions, parameters and places" })
        .fill("length = 130");
    },
  ],
  [
    "agent",
    async (page, api) => {
      api.drip = 2500;
      await page.goto("/p/p1");
      await page.getByLabel("Describe the part").fill("Sensor plate 120 x 80 x 6 mm with four M6 holes");
      await page.getByRole("button", { name: "Generate" }).click();
      const stream = page.getByRole("region", { name: "Generation timeline" });
      await expect(stream.getByRole("listitem").nth(2)).toBeVisible({ timeout: 30_000 });
    },
  ],
  [
    "versions",
    async (page, _api, phone) => {
      await editor(page);
      await page.getByLabel("Plate Length", { exact: true }).fill("130");
      await page.getByLabel("Plate Length", { exact: true }).press("Enter");
      await tab(page, phone, "Versions");
      const lane = page.getByRole("list", { name: "Version history" });
      await expect(lane.locator("strong")).toHaveText(["v2", "v1"], { timeout: 30_000 });
      await page.getByRole("button", { name: "Compare" }).click();
      await lane.getByRole("button", { name: "v1", exact: true }).click();
      await expect(page.getByRole("table", { name: "Parameter diff" })).toBeVisible();
    },
  ],
  [
    "explore",
    async (page) => {
      await page.goto("/explore");
      await expect(page.getByRole("list", { name: "Published parts" }).locator("img").first()).toBeVisible();
    },
  ],
];

for (const [name, shot, scenario] of screens)
  test(`screen ${name}`, async ({ page }) => {
    test.skip(!process.env.SHOTS, "set SHOTS to an output folder");
    test.setTimeout(180_000);
    for (const theme of ["dark", "light"])
      for (const [label, size] of sizes) {
        const api = new MockApi(scenario ?? sensorPlate);
        api.seed();
        await api.install(page);
        await page.setViewportSize(size);
        await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
        await shot(page, api, label === "390");
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${process.env.SHOTS}/${name}-${theme}-${label}.png` });
        await page.unrouteAll({ behavior: "ignoreErrors" });
      }
  });
