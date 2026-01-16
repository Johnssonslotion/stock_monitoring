import { test, expect } from '@playwright/test';

test.describe('Map-First Dashboard Layout', () => {

    test('should start with Map expanded (70%) and Chart collapsed (30%)', async ({ page }) => {
        // 1. Visit Dashboard
        await page.goto('http://localhost:5173/');

        // 2. Check Map visibility
        const mapContainer = page.getByText('Market Map Overview').locator('..').locator('..');
        await expect(mapContainer).toBeVisible();

        // Check if Map is larger than Chart
        const mapBox = await mapContainer.boundingBox();
        const chartBox = await page.getByText('PREVIEW').locator('..').locator('..').boundingBox();

        if (mapBox && chartBox) {
            console.log(`Map Height: ${mapBox.height}, Chart Height: ${chartBox.height}`);
            // Note: In flex-row layout it would be width, but here it looks like flex-row or col depending on verify. 
            // App.tsx uses flex-col inside main. No wait, line 168: <div className="w-full h-full flex gap-2 p-1"> which is row by default.
            // Line 171: animate={{ flex: isMapExpanded ? 7 : 3 }}
            // So width should be compared.
            expect(mapBox.width).toBeGreaterThan(chartBox.width);
        }
    });

    test('should slide up chart when a symbol is clicked', async ({ page }) => {
        await page.goto('http://localhost:5173/');

        // 1. Wait for Map data to load
        await page.waitForSelector('[data-symbol="005930"]', { timeout: 10000 });

        // 2. Click on Samsung Elec using data-symbol attribute on rect
        const symbolElement = page.locator('rect[data-symbol="005930"]').first();
        await symbolElement.click({ force: true });

        // 3. Wait for animation and state update
        await page.waitForTimeout(1000);

        // 3. Verify Chart is now expanded (Analysis Mode)
        const analysisBadge = page.getByText('ANALYSIS');
        await expect(analysisBadge).toBeVisible();

        const mapContainer = page.getByText('Market Map Overview').locator('..').locator('..');
        const chartContainer = analysisBadge.locator('..').locator('..');

        const mapBox = await mapContainer.boundingBox();
        const chartBox = await chartContainer.boundingBox();

        if (mapBox && chartBox) {
            expect(chartBox.width).toBeGreaterThan(mapBox.width);
        }

        // 4. Check URL Sync
        expect(page.url()).toContain('selected=005930');
    });

    test('should load symbol from URL', async ({ page }) => {
        await page.goto('http://localhost:5173/?selected=000660');

        // Wait for effect
        await page.waitForTimeout(500);

        // Should be in Analysis mode
        await expect(page.getByText('ANALYSIS')).toBeVisible();

        // Should show SK하이닉스
        await expect(page.getByText('SK하이닉스 (000660)')).toBeVisible();
    });
});
