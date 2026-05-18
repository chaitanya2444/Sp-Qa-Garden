/**
 * Search Test Suite - Simplified
 */
const { test, expect } = require('@playwright/test');

test.describe('Search', () => {

    test('should fail - search results URL mismatch', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page).toHaveURL('https://example.com/search?q=laptop');
    });

    test('should fail - result count mismatch', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('.search-result-item')).toHaveCount(10);
    });

});
