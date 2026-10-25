import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiPaths = [
  "/health",
  "/projects",
  "/models",
  "/jobs",
  "/batch",
  "/shares",
  "/s/",
  "/hooks",
  "/tokens",
  "/bugs",
  "/docs",
  "/openapi.json",
];
const target = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  // The editor chunk carries three.js and drei.
  build: { chunkSizeWarningLimit: 1100 },
  server: { proxy: Object.fromEntries(apiPaths.map((path) => [path, { target, changeOrigin: true }])) },
  test: {
    environment: "jsdom",
    setupFiles: ["src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
