import { test, expect, type Page } from "@playwright/test";
import { apiRequest, createSession, createStudent, login, registerTutor } from "../fixtures/api";

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

async function assertNoRawUuids(page: Page) {
  expect((await page.locator("body").innerText()).match(UUID)).toBeNull();
}

async function tutorLogin(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
}

test("user-facing views do not expose raw UUIDs", async ({ page, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student = await createStudent(request, tutorToken);
  const start = new Date(Date.now() + 5 * 60 * 1000);
  const session = await createSession(request, tutorToken, student.user_id, start, new Date(start.getTime() + 30 * 60 * 1000));
  await tutorLogin(page, tutor.email, tutor.password);
  await assertNoRawUuids(page);
  await page.goto("/students");
  await assertNoRawUuids(page);
  await page.goto(`/students/${student.id}`);
  await assertNoRawUuids(page);
  await page.goto(`/sessions/${session.id}`);
  await assertNoRawUuids(page);

  const studentToken = await login(request, { email: student.email, password: student.password });
  await page.addInitScript((token) => localStorage.setItem("tutorflow_token", token), studentToken);
  await page.goto("/student/dashboard");
  await assertNoRawUuids(page);
  await page.goto("/student/history");
  await assertNoRawUuids(page);
});
