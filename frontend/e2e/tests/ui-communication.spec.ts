import { test, expect } from "@playwright/test";
import { createSession, createStudent, login, registerTutor } from "../fixtures/api";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

function sessionTime(offsetMinutes: number) {
  return new Date(Date.now() + offsetMinutes * 60 * 1000);
}

test("AI plan and review are visible to tutors and students", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken, { name: "Communication Student" });
  const session = await createSession(request, tutorToken, student.user_id, sessionTime(2), sessionTime(62));

  const planResponse = await request.post(`${API_URL}/sessions/${session.id}/ai-plan`, {
    data: { duration_minutes: 60 },
    headers: { Authorization: `Bearer ${tutorToken}` },
  });
  expect(planResponse.ok()).toBeTruthy();
  const planned = await planResponse.json();
  const planText = planned.ai_plan;

  await page.goto("/login");
  await page.getByLabel("Email").fill(tutor.email);
  await page.getByLabel("Password").fill(tutor.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto(`/sessions/${session.id}`);
  await expect(page.getByRole("heading", { name: "AI Plan" })).toBeVisible();
  await expect(page.locator("body")).toContainText(JSON.parse(planText).main_focus);

  const startResponse = await request.patch(`${API_URL}/sessions/${session.id}/start`, {
    headers: { Authorization: `Bearer ${tutorToken}` },
    data: {},
  });
  expect(startResponse.ok()).toBeTruthy();
  const completeResponse = await request.patch(`${API_URL}/sessions/${session.id}/complete`, {
    headers: { Authorization: `Bearer ${tutorToken}` },
    data: { notes: "Worked through the practice exercise.", homework: "Repeat the exercise once." },
  });
  expect(completeResponse.ok()).toBeTruthy();
  const reviewResponse = await request.patch(`${API_URL}/sessions/${session.id}/trigger-ai-review`, {
    headers: { Authorization: `Bearer ${tutorToken}` },
    data: {},
  });
  expect(reviewResponse.ok()).toBeTruthy();
  const reviewed = await reviewResponse.json();
  const summary = JSON.parse(reviewed.ai_summary);

  await page.goto(`/sessions/${session.id}`);
  await expect(page.getByRole("heading", { name: "AI Summary" })).toBeVisible();
  await expect(page.locator("body")).toContainText(summary.summary);

  await page.evaluate(() => localStorage.removeItem("tutorflow_token"));
  await page.goto("/login");
  await page.getByLabel("Email").fill(student.email);
  await page.getByLabel("Password").fill(student.password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/student\/dashboard/);
  await page.goto(`/student/sessions/${session.id}`);
  await expect(page.getByRole("heading", { name: "AI Plan" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "AI Summary" })).toBeVisible();
  await expect(page.locator("body")).toContainText(summary.summary);
});
