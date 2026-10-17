import { fileURLToPath } from "node:url";
import { defineConfig } from "../../frontend/node_modules/@playwright/test/index.mjs";
export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  outputDir: "../../frontend/output/playwright/results",
  use: {
    baseURL: "http://127.0.0.1:5174",
    headless: true,
    channel: "chrome",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      cwd: fileURLToPath(new URL("../../frontend", import.meta.url)),
      command: "node ../tests/e2e/mock-api.mjs",
      url: "http://127.0.0.1:8788/__test/request",
      reuseExistingServer: false,
    },
    {
      cwd: fileURLToPath(new URL("../../frontend", import.meta.url)),
      command:
        "API_PROXY_TARGET=http://127.0.0.1:8788 npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
    },
  ],
});
