import { test, expect } from '@playwright/test';

/**
  * @author John Doe
  * @createdDate 2025-08-23
  * @updatedDate 2025-10-04
  */ 
test('basic test', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await page.screenshot({path:'screnshot.png',fullPage:true})
  await page.click('text=Get started')
  const title = page.locator('.navbar__inner .navbar__title');
  await expect(title).toHaveText('Playwright');
});
}}
