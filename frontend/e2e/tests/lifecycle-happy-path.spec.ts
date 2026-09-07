import { test, expect } from "@playwright/test";
import { createSession, createStudent, login, registerTutor } from "../fixtures/api";

function sessionTime(offsetMinutes: number) {
  return new Date(Date.now() + offsetMinutes * 60 * 1000);
}

test("tutor can complete the full session lifecycle through the UI", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken, { name: "Lifecycle Student" });
  const session = await createSession(
    request,
    tutorToken,
    student.user_id,
    sessionTime(-5),
    sessionTime(55),
  );

  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto(`/sessions/${session.id}`);

  await expect(page.getByLabel("Session lifecycle: SCHEDULED")).toContainText("Scheduled");
  await page.getByRole("button", { name: "Generate AI Plan" }).click();
  await expect(page.getByRole("heading", { name: "AI Plan" })).toBeVisible({ timeout: 60_000 });

  await page.getByTestId("start-btn").click();
  await expect(page.getByLabel("Session lifecycle: IN_PROGRESS")).toContainText("In Progress");

  await page.getByLabel("Notes").fill("Covered functions and parameter passing.");
  await page.getByLabel("Homework").fill("Write two functions using parameters.");
  await page.getByRole("button", { name: "Complete Session" }).click();
  await expect(page.getByLabel("Session lifecycle: COMPLETED")).toContainText("Completed");

  await page.getByRole("button", { name: "Trigger AI Review" }).click();
  await expect(page.getByRole("heading", { name: "AI Summary" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByLabel("Session lifecycle: AI_REVIEWED")).toContainText("AI Reviewed");
});
