import { existsSync } from 'node:fs';
import { chromium, defineConfig, devices } from '@playwright/test';

function resolveRuntimeChromiumExecutable(): string | undefined {
  const configured = process.env.PURECORTEX_PLAYWRIGHT_EXECUTABLE_PATH;
  if (configured && existsSync(configured)) {
    return configured;
  }

  const expected = chromium.executablePath();
  if (existsSync(expected)) {
    return expected;
  }

  // Cursor runtime occasionally installs x64 browser binaries while Playwright
  // resolves an arm64 default path. Fallback to the x64 sibling path if present.
  const x64Fallback = expected
    .replace('chrome-headless-shell-mac-arm64', 'chrome-headless-shell-mac-x64')
    .replace('/chrome-mac-arm64/', '/chrome-mac-x64/');

  if (existsSync(x64Fallback)) {
    return x64Fallback;
  }

  return undefined;
}

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: 'http://127.0.0.1:3001',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          executablePath: resolveRuntimeChromiumExecutable(),
        },
      },
    },
  ],
  webServer: {
    command: 'npm run dev -- --hostname 127.0.0.1 --port 3001',
    url: 'http://127.0.0.1:3001',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      PURECORTEX_ADMIN_DEV_SESSION_SECRET: 'playwright-local-admin-session',
      NEXT_PUBLIC_API_URL: 'http://127.0.0.1:8000',
    },
  },
});
