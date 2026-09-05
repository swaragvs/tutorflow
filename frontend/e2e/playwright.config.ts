import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: process.env.FRONTEND_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
    channel: "chrome",
    executablePath: process.env.CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  },
  projects: [{
    name: "chromium",
    use: {
      ...devices["Desktop Chrome"],
      browserName: "chromium",
      channel: "chrome",
      executablePath: process.env.CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    },
  }],
});
