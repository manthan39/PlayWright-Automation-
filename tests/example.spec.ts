import { test, expect } from '@playwright/test';

test('basic test', async ({ page }) => {
  /**
 * @author Manthan Bhatiya
 * @createdDate 2025-01-01
 * @updatedDate 2025-02-02
 */
  await page.goto('https://playwright.dev/');
  await page.screenshot({path:'screnshot.png',fullPage:true})
  await page.click('text=Get started')
  const title = page.locator('.navbar__inner .navbar__title');
  await expect(title).toHaveText('Playwright');
});
}}

}

await page.goto('https://playwright.dev/');
await page.goto('https://playwright.dev/');
