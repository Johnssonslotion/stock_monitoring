import { test, expect } from '@playwright/test';

test.describe('Map-First Dashboard Layout', () => {

    test('should start with Map visible and switch to Analysis on click', async ({ page }) => {
        page.on('console', msg => console.log(`[Browser Console]: ${msg.text()} `));
        page.on('pageerror', err => console.log(`[Browser Error]: ${err.message} `));

        // 1. Visit Dashboard
        await page.goto('http://localhost:5173/');

        // 2. Check Map visibility (Dashboard Tab)
        await expect(page.getByText('Market Map Overview').first()).toBeVisible();
        await expect(page.getByText('Professional analysis').first()).toBeHidden();

        // 3. Wait for Map data to load
        // Use a more generic selector or wait for ANY symbol rect
        await page.waitForTimeout(2000); // Give it a moment for mock/real data to render
        const symbolRect = page.locator('[data-symbol="005930"]').first();

        // If 005930 is not found (maybe different mock data), try any rect with data-symbol
        if (await symbolRect.count() === 0) {
            console.log('Samsung not found, clicking first available symbol');
            await page.locator('[data-symbol]').first().click({ force: true });
        } else {
            await symbolRect.click({ force: true });
        }

        // 4. Verify switch to Analysis Tab
        // The App auto-switches tab on click
        await expect(page.getByText('Professional analysis').first()).toBeVisible();

        // 5. Verify Chart presence
        // Chart section has data-testid="chart-section"
        await expect(page.getByTestId('chart-section')).toBeVisible();

        // 6. Check URL Sync
        expect(page.url()).toContain('selected=');
    });

    test('should load symbol from URL and open Analysis tab directly', async ({ page }) => {
        await page.goto('http://localhost:5173/?selected=000660');

        // Wait for effect
        await page.waitForTimeout(1000);

        // Should be in Analysis mode directly
        await expect(page.getByText('Professional analysis').first()).toBeVisible();

        // Should show SK하이닉스 (or whatever symbol name is loaded)
        // Check for specific element like the badge
        await expect(page.locator('span', { hasText: '000660' }).first()).toBeVisible();
    });
});
