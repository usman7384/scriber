import { defineConfig, devices } from "@playwright/test";

const port = 5199;

export default defineConfig({
  testDir: "e2e",
  testIgnore: ["parity/**", "live/**"],
  timeout: 30_000,
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: `http://127.0.0.1:${port}`,
    viewport: { width: 1280, height: 900 },
    // The home globe's spin stalls SwiftShader screenshots; reduced motion draws it once.
    reducedMotion: "reduce",
    launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
  },
  webServer: {
    command: `npx vite --host 127.0.0.1 --port ${port} --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
  },
});
