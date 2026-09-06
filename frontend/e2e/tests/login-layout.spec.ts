import { test, expect } from "@playwright/test";

test("login layout fits the standard laptop viewport", async ({ page }) => {
  await page.goto("/login");

  const submitButton = page.getByRole("button", { name: "Login" });
  await expect(submitButton).toBeVisible();
  await expect(submitButton).toBeInViewport();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();

  const bounds = await page.evaluate(() => {
    const element = document.querySelector<HTMLButtonElement>(".reference-submit");
    if (!element) throw new Error("Submit button not found");
    const rect = element.getBoundingClientRect();
    return {
      bottom: rect.bottom,
      viewportHeight: window.innerHeight,
      bodyScrollHeight: document.body.scrollHeight,
      documentScrollHeight: document.documentElement.scrollHeight,
    };
  });

  expect(bounds.bottom).toBeLessThanOrEqual(bounds.viewportHeight);
  expect(bounds.bodyScrollHeight).toBeLessThanOrEqual(bounds.viewportHeight);
  expect(bounds.documentScrollHeight).toBeLessThanOrEqual(bounds.viewportHeight);
});
