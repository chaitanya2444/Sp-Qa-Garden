/**
 * Checkout Test Suite - Simplified
 */
const { test, expect } = require('@playwright/test');

test.describe('Checkout', () => {

    test('should fail - cart total text mismatch', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('.cart-total-amount')).toHaveText('$99.99');
    });

    test('should fail - checkout button disabled', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('#checkout-proceed-button')).toBeEnabled();
    });

});
