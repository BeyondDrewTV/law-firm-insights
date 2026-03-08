import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const baseURL = process.env.BASE_URL || "http://127.0.0.1:8081";
const useExternalBase = Boolean(process.env.BASE_URL);
const configDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 180_000,
  expect: {
    timeout: 20_000,
  },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL,
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: useExternalBase
    ? undefined
    : {
        command: "npm run dev -- --host 127.0.0.1 --port 8081",
        cwd: configDir,
        url: baseURL,
        timeout: 120_000,
        reuseExistingServer: true,
      },
});
