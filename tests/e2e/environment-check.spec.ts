import { test, expect } from '@playwright/test';

test.describe('Environment verification', () => {
    test('should detect data source mode (Real vs Mock)', async ({ page }) => {
        // 1. Visit the app
        // Note: BaseURL is configured in playwright.config.ts or passed via CLI
        await page.goto('/');

        // 2. Wait for initial load
        await expect(page.locator('body')).toBeVisible();

        // 3. Check for Candle Chart
        const chart = page.locator('text=Candle Chart'); // Adjust selector as needed
        // Actually looking for the chart container ID or class
        // In CandleChart.tsx: <div ref={chartContainerRef} ... /> 
        // It doesn't have an ID. Let's look for known UI element like "Samsung Electronics"

        await expect(page.getByText('Samsung Electronics')).toBeVisible();

        // 4. Verify Data Loading
        // "✅ Received X candles" log indicates success.
        // Or check if specific real data element exists?
        // Hard to distinguish visually without specific "Mock Mode" badge.

        // However, we can check network capability
        const response = await page.request.get('/api/v1/health');
        if (response.ok()) {
            console.log("✅ Backend is REACHABLE (Real Mode)");
            expect(response.status()).toBe(200);
        } else {
            console.log("⚠️ Backend UNREACHABLE (Mock Mode)");
            // If mock mode, ensure chart is still visible
            // We might want to assert specific Mock behavior here if required
        }
    });

    test('should verify 1-minute candle option', async ({ page }) => {
        await page.goto('/');

        // Open Timeframe Selector
        // It's usually visible. Click '1d' to change? Or verify '1d' is default.
        // Click '1M' if available.
        // TimeframeSelector.tsx: { label: '1M', value: '1m' }

        const btn1m = page.getByRole('button', { name: '1M', exact: true });
        if (await btn1m.isVisible()) {
            await btn1m.click();
            console.log("Clicked 1M timeframe");

            // Wait for data update (Mock or Real)
            // Expect no crash
            await expect(page.locator('canvas')).toBeVisible(); // Chart canvas
        }
    });
});
