import { test, expect } from "@playwright/test";
import { apiRequest, createSession, createStudent, login, registerTutor } from "../fixtures/api";

test("started sessions cannot be cancelled or rescheduled", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken);
  const start = new Date(Date.now() + 5 * 60 * 1000);
  const session = await createSession(request, tutorToken, student.user_id, start, new Date(start.getTime() + 30 * 60 * 1000));
  const started = await apiRequest(request, tutorToken, `/sessions/${session.id}/start`, "PATCH", {});
  expect(started.status()).toBe(200);

  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await page.goto(`/sessions/${session.id}`);
  await expect(page.getByTestId("cancel-btn")).toHaveCount(0);
  await expect(page.getByTestId("reschedule-btn")).toHaveCount(0);

  const deleted = await apiRequest(request, tutorToken, `/sessions/${session.id}`, "DELETE");
  expect(deleted.status()).toBe(409);
});
