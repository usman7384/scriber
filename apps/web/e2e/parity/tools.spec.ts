import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";
import type { Printability } from "../../src/api";
import { asset, basePlate, motorHolder, stackScenario, type Scenario } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";

async function openEditor(page: Page, scenario: Scenario, tools = { freecad: true, prusaslicer: true }) {
  const api = new MockApi(scenario);
  api.tools = tools;
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  return api;
}

const freecadItem = (page: Page) => page.getByRole("button", { name: "FreeCAD (.FCStd)" });

async function exportMenu(page: Page) {
  await page.locator("details.menu summary").click();
  await expect(page.getByRole("link", { name: "STEP" })).toBeVisible();
}

test("EX-4 (web) Export offers FreeCAD .FCStd when the API has FreeCAD, and shows why a design cannot map", async ({
  page,
  row,
}) => {
  await openEditor(page, basePlate);
  await exportMenu(page);
  await row.shot("1-menu");
  const download = page.waitForEvent("download");
  await freecadItem(page).click();
  const file = await download;
  const bytes = readFileSync(await file.path());
  const expected = asset("base-plate-t5.FCStd");

  await openEditor(page, stackScenario);
  await exportMenu(page);
  await freecadItem(page).click();
  const alert = page.getByRole("alert");
  await expect(alert).toHaveText(/no FreeCAD export/);
  const message = await alert.textContent();
  await row.shot("2-unsupported");

  await openEditor(page, basePlate, { freecad: false, prusaslicer: true });
  await exportMenu(page);
  const hidden = (await freecadItem(page).count()) === 0;
  await row.shot("3-no-freecad");

  Object.assign(row.measured, {
    file: file.suggestedFilename(),
    bytes: bytes.length,
    same_bytes_as_freecad_output: bytes.equals(expected),
    zip_with_document_xml: bytes.subarray(0, 2).toString("latin1") === "PK" && bytes.includes("Document.xml"),
    unsupported_message: message,
    hidden_without_freecad: hidden,
  });
  expect(file.suggestedFilename()).toBe("base-plate-v1.FCStd");
  expect(bytes.equals(expected)).toBe(true);
  expect(row.measured.zip_with_document_xml).toBe(true);
  expect(message).toBe(
    "this design has no FreeCAD export: assembly joints and placements have no FreeCAD export yet",
  );
  expect(hidden).toBe(true);
  row.note =
    "Export route mocked with the API's status codes and wording (apps/api tools.py); the .FCStd bytes and the unsupported message are FreeCAD 1.1.4 and fcstd_plan output written by e2e/fixtures/make_fixtures.py. The real route is apps/api tests/test_tools.py.";
});

test("VM-9 (web) Check printability shows the PrusaSlicer report beside the manufacturability findings", async ({
  page,
  row,
}) => {
  const api = await openEditor(page, motorHolder);
  const panel = page.getByLabel("Printability", { exact: true });
  await panel.getByRole("button", { name: "Check printability" }).click();
  await expect(panel.getByText(/layers/)).toBeVisible();
  await row.shot("1-report");
  const slices = api.requests.filter((r) => r.method === "POST" && r.path === "/models/m1/slice");
  const report = (await page.evaluate(() =>
    fetch("/models/m1/slice?version=1", { method: "POST" }).then((r) => r.json()),
  )) as Printability;
  const summary = await panel.getByText(/layers/).textContent();
  const findingsFirst = await page.evaluate(() => {
    const [findings, print] = ["Checks and findings", "Printability"].map((l) =>
      document.querySelector(`[aria-label="${l}"]`),
    );
    return (
      !!findings && !!print && !!(findings.compareDocumentPosition(print) & Node.DOCUMENT_POSITION_FOLLOWING)
    );
  });

  await openEditor(page, motorHolder, { freecad: true, prusaslicer: false });
  const hidden = (await page.getByRole("button", { name: "Check printability" }).count()) === 0;
  await row.shot("2-no-prusaslicer");

  Object.assign(row.measured, {
    slice_requests: slices.length,
    shown: summary,
    verdict: report.ok,
    layers: report.layers,
    gcode_bytes: report.gcode_bytes,
    manifold: report.manifold,
    warnings: report.warnings.length,
    errors: report.errors.length,
    below_findings: findingsFirst,
    hidden_without_prusaslicer: hidden,
  });
  expect(slices).toHaveLength(1);
  expect(summary).toBe(`${report.layers} layers, ${(report.gcode_bytes / 1e6).toFixed(2)} MB of G-code`);
  expect(report.ok && report.manifold).toBe(true);
  await expect(page.getByLabel("Printability", { exact: true })).toHaveCount(0);
  expect(findingsFirst).toBe(true);
  expect(hidden).toBe(true);
  row.note =
    "Slice route mocked with the API's response shape; the report is PrusaSlicer 2.9.6 on the motor holder STL (e2e/fixtures/external-tools.json from make_fixtures.py). The real route is apps/api tests/test_tools.py.";
});
