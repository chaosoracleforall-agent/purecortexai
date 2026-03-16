import { expect, test } from '@playwright/test';

test('admin proxy rejects a spoofed auth email header by default', async ({ request }) => {
  const response = await request.get('/admin-api/control-plane', {
    headers: {
      'x-purecortex-auth-email': 'chaosoracleforall@gmail.com',
    },
  });

  expect(response.status()).toBe(403);
  expect(await response.json()).toEqual({ detail: 'Admin SSO required' });
  expect(response.headers()['cache-control']).toContain('no-store');
});

test('admin proxy marks authenticated control-plane responses as no-store', async ({ request }) => {
  const loginResponse = await request.post('/admin-api/dev-session', {
    data: {
      email: 'chaosoracleforall@gmail.com',
    },
  });

  expect(loginResponse.status()).toBe(200);

  const response = await request.get('/admin-api/control-plane');
  expect(response.headers()['cache-control']).toContain('no-store');
});

test('admin dashboard approves a request and reveals the issued secret', async ({ page }) => {
  const health = {
    status: 'ok',
    surface: 'internal-admin',
    owner_emails: ['chaosoracleforall@gmail.com'],
    database_configured: true,
    oauth_configured: true,
    ip_trust_configured: true,
  };

  let requests = [
    {
      id: 'req-1',
      requester_name: 'Alice Example',
      requester_email: 'alice@example.com',
      organization: 'Example Org',
      requested_access_level: 'write',
      requested_surfaces: ['api', 'cli'],
      requested_ips: ['203.0.113.10/32'],
      use_case: 'Need write access for CLI-driven governance automation.',
      status: 'pending',
      review_notes: null,
      issued_key_id: null,
      created_at: '2026-03-16T00:00:00Z',
    },
  ];

  let apiKeys: Array<Record<string, unknown>> = [];
  let approvePayload: Record<string, unknown> | null = null;

  await page.route('**/admin-api/control-plane', async (route) => {
    await route.fulfill({ json: health });
  });

  await page.route(/.*\/admin-api\/requests(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({
      json: {
        total: requests.length,
        requests,
      },
    });
  });

  await page.route(/.*\/admin-api\/keys(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({
      json: {
        total: apiKeys.length,
        api_keys: apiKeys,
      },
    });
  });

  await page.route('**/admin-api/requests/req-1/approve', async (route) => {
    approvePayload = route.request().postDataJSON() as Record<string, unknown>;
    requests = [
      {
        ...requests[0],
        status: 'approved',
        review_notes: String(approvePayload.review_notes ?? ''),
        issued_key_id: 'key-001',
      },
    ];
    apiKeys = [
      {
        id: 'api-key-row-1',
        key_id: 'key-001',
        key_prefix: 'ctx_key-001',
        label: 'Alice Example primary key',
        owner_name: 'Alice Example',
        owner_email: 'alice@example.com',
        status: 'active',
        access_level: 'write',
        scopes: ['agent.chat', 'governance.write', 'read.public'],
        intended_surfaces: ['api', 'cli'],
        rate_limit_profile: 'write-default',
        expires_at: null,
        last_used_at: null,
        last_used_ip: null,
        override_no_ip_allowlist: false,
        notes: String(approvePayload.review_notes ?? ''),
        ip_allowlists: [{ cidr: '203.0.113.10/32', label: null }],
      },
    ];

    await route.fulfill({
      json: {
        request: requests[0],
        api_key: apiKeys[0],
        secret: 'ctx_key-001_secret-value',
      },
    });
  });

  await page.goto('/admin');

  await expect(page.getByRole('heading', { name: /owner dashboard/i })).toBeVisible();
  await expect(page.getByText('alice@example.com')).toBeVisible();

  await page.getByLabel('Review Notes').fill('Approved for CLI beta validation.');
  await page.getByRole('button', { name: /approve & issue key/i }).click();

  await expect(page.getByText(/approved alice@example\.com and issued a new api key\./i)).toBeVisible();
  await expect(page.getByText(/one-time secret reveal/i)).toBeVisible();
  await expect(page.getByText('ctx_key-001_secret-value')).toBeVisible();

  expect(approvePayload).toEqual({
    review_notes: 'Approved for CLI beta validation.',
    label: 'Alice Example primary key',
    ip_allowlists: [{ cidr: '203.0.113.10/32', label: null }],
    expires_in_days: null,
  });
});

test('admin dashboard saves key policy updates and rotates a key', async ({ page }) => {
  const health = {
    status: 'ok',
    surface: 'internal-admin',
    owner_emails: ['chaosoracleforall@gmail.com'],
    database_configured: true,
    oauth_configured: true,
    ip_trust_configured: true,
  };

  const requests: Array<Record<string, unknown>> = [];
  let apiKeys: Array<Record<string, unknown>> = [
    {
      id: 'api-key-row-1',
      key_id: 'key-001',
      key_prefix: 'ctx_key-001',
      label: 'Owner primary key',
      owner_name: 'Owner',
      owner_email: 'owner@example.com',
      status: 'active',
      access_level: 'write',
      scopes: ['agent.chat', 'governance.write', 'read.public'],
      intended_surfaces: ['api', 'cli'],
      rate_limit_profile: 'write-default',
      expires_at: null,
      last_used_at: null,
      last_used_ip: null,
      override_no_ip_allowlist: false,
      notes: 'Initial note',
      ip_allowlists: [{ cidr: '203.0.113.10/32', label: null }],
    },
  ];

  let savePayload: Record<string, unknown> | null = null;
  let rotatePayload: Record<string, unknown> | null = null;

  await page.route('**/admin-api/control-plane', async (route) => {
    await route.fulfill({ json: health });
  });

  await page.route(/.*\/admin-api\/requests(\?.*)?$/, async (route) => {
    await route.fulfill({
      json: {
        total: requests.length,
        requests,
      },
    });
  });

  await page.route(/.*\/admin-api\/keys(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({
      json: {
        total: apiKeys.length,
        api_keys: apiKeys,
      },
    });
  });

  await page.route('**/admin-api/keys/key-001', async (route) => {
    savePayload = route.request().postDataJSON() as Record<string, unknown>;
    apiKeys = [
      {
        ...apiKeys[0],
        label: savePayload.label,
        scopes: savePayload.scopes,
        ip_allowlists: savePayload.ip_allowlists,
        notes: savePayload.notes,
        override_no_ip_allowlist: savePayload.override_no_ip_allowlist,
      },
    ];
    await route.fulfill({
      json: {
        api_key: apiKeys[0],
      },
    });
  });

  await page.route('**/admin-api/keys/key-001/rotate', async (route) => {
    rotatePayload = route.request().postDataJSON() as Record<string, unknown>;
    apiKeys = [
      {
        ...apiKeys[0],
        id: 'api-key-row-2',
        key_id: 'key-002',
        key_prefix: 'ctx_key-002',
        label: 'Owner primary key v2',
        notes: rotatePayload.reason,
      },
    ];
    await route.fulfill({
      json: {
        api_key: apiKeys[0],
        secret: 'ctx_key-002_rotated-secret',
      },
    });
  });

  await page.goto('/admin');

  await page.getByLabel('Label').fill('Owner primary key v2');
  await page.getByLabel('Scopes').fill('agent.chat, governance.write, mcp.write, read.public');
  await page.getByLabel('IP Allowlists').fill('198.51.100.0/24\n203.0.113.10/32');
  await page.getByLabel('Notes / Rotation Reason').fill('Quarterly owner rotation.');
  await page.getByLabel(/allow empty ip allowlist for this key/i).check();
  await page.getByRole('button', { name: /save policy/i }).click();

  await expect(page.getByText(/updated policy for key-001\./i)).toBeVisible();
  expect(savePayload).toEqual({
    label: 'Owner primary key v2',
    scopes: ['agent.chat', 'governance.write', 'mcp.write', 'read.public'],
    ip_allowlists: [
      { cidr: '198.51.100.0/24', label: null },
      { cidr: '203.0.113.10/32', label: null },
    ],
    notes: 'Quarterly owner rotation.',
    override_no_ip_allowlist: true,
  });

  await page.getByRole('button', { name: /^rotate$/i }).click();

  await expect(page.getByText(/rotated key-001\./i)).toBeVisible();
  await expect(page.getByText(/ctx_key-002_rotated-secret/i)).toBeVisible();
  expect(rotatePayload).toEqual({
    reason: 'Quarterly owner rotation.',
  });
});
