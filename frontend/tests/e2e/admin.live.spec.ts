import { expect, test, type APIRequestContext, type BrowserContext, type Locator, type Page } from '@playwright/test';

const RUN_LIVE = process.env.PURECORTEX_RUN_LIVE_ADMIN_E2E === '1';
const BACKEND_URL = process.env.PURECORTEX_E2E_BACKEND_URL || 'http://127.0.0.1:8000';
const ADMIN_EMAIL = process.env.PURECORTEX_ADMIN_E2E_EMAIL || 'chaosoracleforall@gmail.com';
const AUTH_MODE = process.env.PURECORTEX_ADMIN_E2E_AUTH_MODE || 'dev-session';

function uniqueSuffix(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function keyIdFromSecret(secret: string): string {
  const parts = secret.split('_');
  if (parts.length < 3 || !parts[1]) {
    throw new Error(`Unexpected API key format: ${secret}`);
  }
  return parts[1];
}

function requestCard(page: Page, email: string): Locator {
  return page.locator(
    `xpath=(//div[contains(@class,'p-5')][contains(., "${email}")][.//button[contains(normalize-space(), "Approve & Issue Key")]])[1]`
  );
}

function keyCard(page: Page, email: string, keyId: string): Locator {
  return page.locator(
    `xpath=(//div[contains(@class,'p-5')][contains(., "${email}")][contains(., "${keyId}")][.//button[normalize-space()="Rotate"]])[1]`
  );
}

async function seedDeveloperAccessRequest(request: APIRequestContext) {
  const suffix = uniqueSuffix();
  const email = `live-admin-e2e-${suffix}@example.com`;
  const response = await request.post(`${BACKEND_URL}/api/developer-access/requests`, {
    data: {
      requester_name: 'Live Admin E2E',
      requester_email: email,
      organization: 'playwright-live',
      use_case: 'Exercise the live admin control plane against a real backend and database.',
      requested_surfaces: ['api', 'cli', 'python_sdk', 'typescript_sdk', 'mcp'],
      requested_access_level: 'custom',
      requested_ips: ['127.0.0.1/32'],
      expected_rpm: 60,
    },
  });

  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  expect(payload.requester_email).toBe(email);
  return { email, requestId: String(payload.id) };
}

async function authenticateAdmin(page: Page) {
  if (AUTH_MODE === 'dev-session') {
    await page.goto('/admin/login');
    await page.getByLabel('Allowed Admin Email').fill(ADMIN_EMAIL);
    await page.getByRole('button', { name: /continue to admin/i }).click();
    await page.waitForURL('**/admin');
    return;
  }

  throw new Error(`Unsupported PURECORTEX_ADMIN_E2E_AUTH_MODE: ${AUTH_MODE}`);
}

test.describe.serial('live admin dashboard', () => {
  test.skip(!RUN_LIVE, 'Set PURECORTEX_RUN_LIVE_ADMIN_E2E=1 to run against a live stack.');

  test('approves, rotates, and revokes a live request', async ({ browser, request, baseURL }) => {
    let context: BrowserContext | undefined;
    try {
      context = await browser.newContext({
        baseURL,
      });

      const page = await context.newPage();
      const seeded = await seedDeveloperAccessRequest(request);

      await authenticateAdmin(page);
      await expect(page.getByRole('heading', { name: /owner dashboard/i })).toBeVisible();
      await expect(page.getByText(seeded.email)).toBeVisible();

      const pending = requestCard(page, seeded.email);
      await expect(pending).toBeVisible();
      await pending.locator('textarea').nth(1).fill('Approved during automated live Playwright validation.');
      await pending.getByRole('button', { name: /approve & issue key/i }).click();

      await expect(page.getByText(new RegExp(`Approved ${seeded.email.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} and issued a new API key\\.`, 'i'))).toBeVisible();

      const issuedSecret = (await page.locator('div.break-all').first().textContent())?.trim();
      expect(issuedSecret).toBeTruthy();
      const firstKeyId = keyIdFromSecret(issuedSecret || '');

      const firstKeyCard = keyCard(page, seeded.email, firstKeyId);
      await expect(firstKeyCard).toContainText(firstKeyId);
      await firstKeyCard.locator('textarea').nth(1).fill('Rotate during automated live Playwright validation.');
      await firstKeyCard.getByRole('button', { name: /^rotate$/i }).click();

      await expect(page.getByText(new RegExp(`Rotated ${firstKeyId}\\. A new secret has been issued below\\.`, 'i'))).toBeVisible();
      const rotatedSecret = (await page.locator('div.break-all').first().textContent())?.trim();
      expect(rotatedSecret).toBeTruthy();
      const rotatedKeyId = keyIdFromSecret(rotatedSecret || '');

      const rotatedKeyCard = keyCard(page, seeded.email, rotatedKeyId);
      await expect(rotatedKeyCard).toContainText(rotatedKeyId);
      await expect(firstKeyCard).toContainText(/revoked/i);
      await rotatedKeyCard.locator('textarea').nth(1).fill('Revoke replacement key during automated live Playwright validation.');
      await rotatedKeyCard.getByRole('button', { name: /^revoke$/i }).click();

      await expect(rotatedKeyCard).toContainText(/revoked/i);

      const revokedResponse = await request.fetch(`${BACKEND_URL}/api/chat/session`, {
        method: 'POST',
        headers: { 'X-API-Key': rotatedSecret || '' },
      });
      expect(revokedResponse.status()).toBe(401);
      await expect(page.getByText(seeded.email).first()).toBeVisible();
    } finally {
      await context?.close();
    }
  });
});
