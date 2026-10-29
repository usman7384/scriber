import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

const stamp = new Date()
  .toLocaleString("sv-SE")
  .replace(/\D/g, "")
  .replace(/^(\d{8})/, "$1-");
// Set once in the runner process; workers inherit it, so every row lands in the same run folder.
process.env.PARITY_RUN ??= stamp;

export default defineConfig({
  ...base,
  testDir: "e2e/parity",
  testIgnore: [],
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: { ...base.use, video: { mode: "on", size: { width: 1280, height: 900 } } },
});
