import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";

const uvCommand = JSON.stringify(process.env.ASTRA_UV ?? "uv");
const localPython = "../.venv/bin/python";
const backendCommand =
  process.env.ASTRA_BACKEND_COMMAND ??
  (existsSync(localPython)
    ? "cd .. && PYTHONPATH=src .venv/bin/python -m uvicorn astra.api.app:app --host 127.0.0.1 --port 8000"
    : `cd .. && PYTHONPATH=src UV_CACHE_DIR=.uv-cache ${uvCommand} run uvicorn astra.api.app:app --host 127.0.0.1 --port 8000`);

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  fullyParallel: true,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: backendCommand,
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
