import { test, expect } from "@playwright/test";
import { createSession, createStudent, login, registerTutor } from "../fixtures/api";

function localInput(date: Date) {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

test("scheduled sessions can be rescheduled with conflict protection", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken);
  const base = Date.now() + 60 * 60 * 1000;
  const sessionA = await createSession(request, tutorToken, student.user_id, new Date(base), new Date(base + 30 * 60 * 1000));
  const sessionBStart = new Date(base + 2 * 60 * 60 * 1000);
  await createSession(request, tutorToken, student.user_id, sessionBStart, new Date(sessionBStart.getTime() + 30 * 60 * 1000));

  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto(`/sessions/${sessionA.id}`);
  await expect(page.getByTestId("reschedule-btn")).toBeVisible();
  await page.getByTestId("reschedule-btn").click();
  await page.getByTestId("reschedule-start-input").fill(localInput(new Date(base + 2 * 60 * 60 * 1000 + 5 * 60 * 1000)));
  await page.getByTestId("reschedule-end-input").fill(localInput(new Date(base + 2 * 60 * 60 * 1000 + 20 * 60 * 1000)));
  await page.getByTestId("reschedule-submit-btn").click();
  await expect(page.getByTestId("error-message")).toContainText(/conflict/i);

  const freeStart = new Date(base + 4 * 60 * 60 * 1000);
  await page.getByTestId("reschedule-start-input").fill(localInput(freeStart));
  await page.getByTestId("reschedule-end-input").fill(localInput(new Date(freeStart.getTime() + 30 * 60 * 1000)));
  await page.getByTestId("reschedule-submit-btn").click();
  await expect(page.getByTestId("error-message")).toHaveCount(0);
  await expect(page.locator("body")).toContainText("Time:");
});
