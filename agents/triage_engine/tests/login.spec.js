/**
 * Login Test Suite - Simplified
 */
const { test, expect } = require('@playwright/test');

test.describe('Login', () => {

    test('should fail - incorrect page title', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page).toHaveTitle('Login Portal - Example App');
    });

    test('should fail - login button not visible', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('#submit-login-button')).toBeVisible();
    });

    test('should fail with invalid password', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('#error-message')).toBeVisible();
    });

});
