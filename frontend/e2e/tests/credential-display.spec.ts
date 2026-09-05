import { test, expect } from "@playwright/test";
import { login, registerTutor } from "../fixtures/api";

test("credential display is one-time", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const token = await login(request, tutor);
  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto("/students");
  await expect(page).toHaveURL(/students$/);
  await page.getByRole("button", { name: "Add Student" }).click();

  const studentEmail = `credential-${Date.now()}@example.com`;
  const studentPassword = "StudentPass123!";
  await page.getByLabel("Name").fill("Credential Student");
  await page.getByLabel("Email").fill(studentEmail);
  await page.getByLabel("Initial password").fill(studentPassword);
  await page.getByRole("button", { name: "Create student" }).click();

  const panel = page.getByTestId("credential-panel");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText(studentEmail);
  await expect(panel).toContainText(studentPassword);
  await page.reload();
  await expect(page.getByTestId("credential-panel")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(studentPassword);
});
