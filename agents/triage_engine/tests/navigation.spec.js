/**
 * Navigation Test Suite - Simplified
 */
const { test, expect } = require('@playwright/test');

test.describe('Navigation', () => {

    test('should fail - menu not visible', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('.main-navigation-menu')).toBeVisible();
    });

    test('should fail - footer links count', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('footer a')).toHaveCount(15);
    });

});
