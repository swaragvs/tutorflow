import { test, expect } from "@playwright/test";
import { createSession, createStudent, login, registerTutor } from "../fixtures/api";

test("early starts are blocked and in-window starts succeed", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken);
  const early = new Date(Date.now() + 60 * 60 * 1000);
  const earlySession = await createSession(request, tutorToken, student.user_id, early, new Date(early.getTime() + 30 * 60 * 1000));

  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto(`/sessions/${earlySession.id}`);
  await expect(page.getByTestId("start-btn")).toBeVisible();
  await page.getByTestId("start-btn").click();
  await expect(page.getByTestId("error-message")).toContainText(/earliest allowed/i);

  const allowed = new Date(Date.now() + 5 * 60 * 1000);
  const allowedSession = await createSession(request, tutorToken, student.user_id, allowed, new Date(allowed.getTime() + 30 * 60 * 1000));
  await page.goto(`/sessions/${allowedSession.id}`);
  await expect(page.getByTestId("start-btn")).toBeVisible();
  await page.getByTestId("start-btn").click();
  await expect(page.locator(".status-in_progress")).toContainText("In Progress");
});
