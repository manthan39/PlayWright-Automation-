import { test, expect } from '@playwright/test';
/**
 * @author Manthan Doe
 * @createdDate 2025-02-34
 * @updatedDate 2025-03-23
 */
test('basic test', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await page.screenshot({path:'screnshot.png',fullPage:true})
  await page.click('text=Get started')
  const title = page.locator('.navbar__inner .navbar__title');
  await expect(title).toHaveText('Playwright');
});
}}
