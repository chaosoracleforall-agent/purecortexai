import { expect, test } from '@playwright/test';

test('governance proposals tab renders live API proposals', async ({ page }) => {
  await page.route('http://127.0.0.1:8000/api/governance/overview', async (route) => {
    await route.fulfill({
      json: {
        total_proposals: 1,
        active_proposals: 1,
        voting_proposals: 1,
        passed_proposals: 0,
        rejected_proposals: 0,
        total_votes: 3,
      },
    });
  });

  await page.route('http://127.0.0.1:8000/api/governance/proposals', async (route) => {
    await route.fulfill({
      json: {
        total: 1,
        proposals: [
          {
            id: 42,
            title: 'Smoke Proposal',
            type: 'general',
            status: 'voting',
            proposer: 'senator',
            created_at: '2026-03-15T18:10:33.745613+00:00',
            votes_for: 3,
            votes_against: 0,
            voter_count: 3,
            curator_reviewed: true,
          },
        ],
      },
    });
  });

  await page.goto('/governance');
  await page.getByRole('button', { name: /proposals/i }).click();

  await expect(page.getByText(/live governance proposals/i)).toBeVisible();
  await expect(page.getByText('Smoke Proposal')).toBeVisible();
  await expect(page.getByText(/curator reviewed/i)).toBeVisible();
});
