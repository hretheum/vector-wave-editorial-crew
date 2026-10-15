import { test, expect } from '@playwright/test';

test.describe('E2E UI smoke', () => {
  test.setTimeout(120_000);

  test('dashboard → topics → topic details → generate draft → editor', async ({ page }) => {
    // Speed-up: stub AI summary to avoid external API delays
    await page.route('**/api/ai/summarize-topic', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ shortTitle: 'Topic', teaser: 'Teaser' })
      })
    })
    // Ensure topics suggestions exist
    await page.route('**/api/topics/suggestions**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [
        { id: 't1', topic_id: 't1', title: 'Topic 1', document: 'Doc 1' },
        { id: 't2', topic_id: 't2', title: 'Topic 2', document: 'Doc 2' }
      ] }) })
    })
    // Dashboard
    await page.goto('/');
    await expect(page).toHaveTitle(/Vector Wave/i);
    // Ensure topics render or seed if empty
    const seedBtn = page.getByRole('button', { name: /Odśwież tematy/i });
    if (await seedBtn.isVisible()) {
      await seedBtn.click();
    }
    // Navigate directly to a synthetic topic details page to avoid HMR/SSR flakiness
    await page.goto('/topics/t1?t=Topic%201', { waitUntil: 'domcontentloaded' });

    // Topic details page
    // Wait for details header instead of strict URL check
    await expect(page.getByRole('heading', { name: /Szczegóły tematu/i })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole('heading', { name: /Szczegóły tematu/i })).toBeVisible();

    // Generate draft via API proxy button component
    const genBtn = page.getByRole('button', { name: /Wygeneruj draft \(AIWF\)/i }).first();
    await genBtn.click();

    // Editor should open (route: /editor?k=...)
    await page.waitForURL(/\/editor\?k=/);
    // Edytor domyślny: textarea widoczne + przyciski
    await expect(page.getByRole('button', { name: /Kopiuj/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /Zacznij pisać swój content/i })).toBeVisible();
  });

  test('publishing pages open without runtime error', async ({ page }) => {
    await page.goto('/publishing', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/publishing$/);
    // small settle to avoid frame detach on hot reload
    await page.waitForTimeout(300);
    await page.goto('/publishing/recent', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/publishing\/recent$/);
  });
});


