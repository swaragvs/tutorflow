import { test, expect } from "@playwright/test";
import { createStudent, login, registerTutor } from "../fixtures/api";

test("tutor can edit a student name", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken, { name: "Before Edit" });

  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto(`/students/${student.id}`);
  await expect(page.getByRole("button", { name: "Edit student" })).toBeVisible();
  await page.getByRole("button", { name: "Edit student" }).click();
  await page.getByTestId("student-name-input").fill("After Edit");
  await page.getByTestId("save-student-btn").click();
  await expect(page.locator("body")).toContainText("After Edit");
  await page.reload();
  await expect(page.locator("body")).toContainText("After Edit");
});
