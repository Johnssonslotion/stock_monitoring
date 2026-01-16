import { test, expect } from '@playwright/test';

test.describe('UI Refinement & Granular Verification', () => {
    test.slow(); // Increase timeout to 90s


    test.beforeEach(async ({ page }) => {
        // 공통 진입 절차:
        await page.goto('http://localhost:5173/');
        // Wait for connection
        await page.waitForTimeout(2000);

        // Ensure we are on Map (Dashboard) - Default
        const mapButton = page.locator('button:has-text("Map")');
        if (await mapButton.isVisible()) {
            await mapButton.click({ force: true });
        }

        // Select a stock (Samsung SDI) from the Map
        console.log('🔹 Waiting for Stock 006400 on Map...');
        try {
            const stockElement = page.locator('[data-symbol="006400"]').first();
            await expect(stockElement).toBeVisible({ timeout: 5000 });
            console.log('🔹 Clicking Stock 006400 on Map...');
            await stockElement.click({ force: true });
        } catch (e) {
            console.log('❌ Stock 006400 NOT found. Listing all available symbols:');
            const symbols = await page.locator('[data-symbol]').evaluateAll(els => els.map(e => e.getAttribute('data-symbol')));
            console.log(symbols);
            throw e;
        }

        // This should auto-navigate to Analysis tab
        console.log('🔹 Waiting for Analysis Tab...');
        await expect(page.locator('text=Professional analysis')).toBeVisible({ timeout: 10000 });

        console.log('🔹 Waiting for Chart Section...');
        await expect(page.locator('[data-testid="chart-section"]')).toBeVisible();
    });

    // 1. 레이아웃 검증 (Split View)
    test('Layout: Market Info Panel should show Split View (News & Related)', async ({ page }) => {
        // [Debug] Check if Market Info Panel base exists
        console.log('🔹 Checking Market Info Panel...');
        await expect(page.locator('text=Market Insights')).toBeVisible({ timeout: 10000 });

        // [Related Stocks Header]
        console.log('🔹 Checking Related Stocks Header...');
        await expect(page.locator('text=Related Stocks in Sector')).toBeVisible();

        // [News Header]
        console.log('🔹 Checking News Header...');
        await expect(page.getByText('Recent News & Sentiment')).toBeVisible({ timeout: 10000 });

        console.log('✅ Split View Layout Verified');
    });

    // 2. 줌 컨트롤 위치 검증
    test('UI: Zoom Controls should be positioned at Top-Right aligned with Timeframe', async ({ page }) => {
        console.log('🔹 Checking Zoom Controls...');
        // top-3 class를 포함하는지 확인 (right-64 for alignment)
        const zoomControls = page.locator('div.absolute.top-3.right-64.z-10.flex.gap-1');
        await expect(zoomControls).toBeVisible();
    });

    // 3. 분봉 전환 기능 검증
    test('Feature: Interval Switch (1M) should trigger update', async ({ page }) => {
        console.log('🔹 Checking Interval Switch...');
        const button1M = page.locator('button:has-text("1M")');
        await expect(button1M).toBeVisible();

        // Click 1M
        await button1M.click();

        // Button should become active (text-white)
        await expect(button1M).toHaveClass(/text-white/);

        // Verify Chart remains visible (no crash)
        await expect(page.locator('[data-testid="chart-section"]')).toBeVisible();
    });

    // 4. 차트 오버플로우 방지 검증 (Resizing/Scaling 대응)
    test('Layout: Chart container should hide overflow', async ({ page }) => {
        console.log('🔹 Checking Overflow...');
        const chartContainer = page.locator('[data-testid="chart-section"]');

        // CSS Property check
        const overflow = await chartContainer.evaluate((el) => {
            return window.getComputedStyle(el).overflow;
        });
        expect(overflow).toBe('hidden');
    });

});
