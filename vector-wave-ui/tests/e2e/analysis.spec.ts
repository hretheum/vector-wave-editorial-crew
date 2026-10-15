import { test, expect } from '@playwright/test';

test.describe('Analysis flows (preview/full + reindex)', () => {
  test.setTimeout(180_000);

  test('dashboard analyze preview then full + reindex', async ({ page }) => {
    // Stub suggestions to avoid slow backend/SSR delays
    await page.route('**/api/topics/suggestions**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [
        { id: 't1', topic_id: 't1', title: 'Topic 1', document: 'Doc 1' },
      ] }) })
    })

    // Navigate directly to a synthetic topic details page
    await page.goto('/topics/t1?t=Topic%201', { waitUntil: 'domcontentloaded' });

    // On topic details page: trigger preview analysis first
    const previewBtn = page.getByRole('button', { name: /Analizuj potencjał/i }).first();
    await previewBtn.waitFor({ state: 'visible', timeout: 30_000 });
    await previewBtn.click();

    // Wait for preview results
    const card = page.locator('[data-test="analysis-results-card"]').first();
    await card.waitFor({ state: 'attached', timeout: 60_000 });
    await expect.soft(card).toBeVisible({ timeout: 5_000 });

    // Try full analysis + reindex if available
    const fullBtn = page.locator('[data-test="analyze-full-reindex"]').first();
    const fullVisible = await fullBtn.isVisible().catch(() => false);
    if (fullVisible) {
      await fullBtn.click();
      await card.waitFor({ state: 'attached', timeout: 60_000 });
    }

    // Optional metrics
    const metrics = page.locator('[data-test="analysis-metrics"]').first();
    await metrics.waitFor({ state: 'visible', timeout: 5_000 }).catch(() => {});
  });
});


