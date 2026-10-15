import { test, expect } from '@playwright/test';

test.describe('Generate draft from topics/[id]', () => {
  test.setTimeout(90_000);

  test('verify generator and warnings in /api/generate-draft response', async ({ page }) => {
    // Speed-up: stub AI summary on topics list
    await page.route('**/api/ai/summarize-topic', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ shortTitle: 'Topic', teaser: 'Teaser' }) })
    })
    // Stub suggestions to ensure links render
    await page.route('**/api/topics/suggestions**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [
        { id: 't1', topic_id: 't1', title: 'Topic 1', document: 'Doc 1' }
      ] }) })
    })
    // Navigate directly to a synthetic topic details page
    await page.goto('/topics/t1?t=Topic%201', { waitUntil: 'domcontentloaded' });

    // Open first topic details (or ensure if missing id)
    // Already on details page

    // We are on topic details page
    await expect(page.getByRole('heading', { name: /Szczegóły tematu/i })).toBeVisible({ timeout: 20_000 });

    // Intercept the API call and assert payload
    const respPromise = page.waitForResponse((resp) => {
      return resp.url().includes('/api/generate-draft') && resp.request().method() === 'POST';
    }, { timeout: 45_000 });

    // Click the UI button which triggers the API call
    await page.getByRole('button', { name: /Wygeneruj draft \(AIWF\)/i }).first().click();

    const resp = await respPromise;
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();

    // Validate normalized shape
    expect(data).toHaveProperty('success', true);
    expect(data).toHaveProperty('draft');
    expect(typeof data.draft.content).toBe('string');
    expect(data.draft.content.length).toBeGreaterThan(20);
    // generator present and not fallback
    expect(typeof data.draft.generator === 'string' || data.draft.generator === null).toBeTruthy();
    if (typeof data.draft.generator === 'string') {
      expect(data.draft.generator.toLowerCase()).not.toContain('fallback');
    }
    // warnings array (may be empty)
    expect(Array.isArray(data.draft.warnings)).toBeTruthy();

    // Should navigate to editor eventually
    await page.waitForURL(/\/editor\?k=/, { timeout: 45_000 });
  });
});


