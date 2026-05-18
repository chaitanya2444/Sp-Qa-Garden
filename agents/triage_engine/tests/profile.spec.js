/**
 * Profile Test Suite - Simplified
 */
const { test, expect } = require('@playwright/test');

test.describe('Profile', () => {

    test('should fail - profile picture not visible', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page.locator('.user-profile-picture')).toBeVisible();
    });

    test('should fail - settings page title', async ({ page }) => {
        await page.goto('https://example.com');
        await expect(page).toHaveTitle('Account Settings - User Profile');
    });

});
