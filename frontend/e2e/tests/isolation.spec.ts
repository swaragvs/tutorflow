import { test, expect } from "@playwright/test";
import { createSession, createStudent, login, registerTutor } from "../fixtures/api";

test("separate browser contexts keep identities isolated", async ({ browser, request }) => {
  const tutor = await registerTutor(request);
  const tutorToken = await login(request, tutor);
  const student1 = await createStudent(request, tutorToken, { name: "Student One" });
  const student2 = await createStudent(request, tutorToken, { name: "Student Two" });
  const start = new Date(Date.now() - 5 * 60 * 1000);
  const session1 = await createSession(request, tutorToken, student1.user_id, start, new Date(start.getTime() + 30 * 60 * 1000));
  const session2 = await createSession(request, tutorToken, student2.user_id, new Date(start.getTime() + 60 * 60 * 1000), new Date(start.getTime() + 90 * 60 * 1000));

  const tutorContext = await browser.newContext();
  const student1Context = await browser.newContext();
  const student2Context = await browser.newContext();
  const tutorPage = await tutorContext.newPage();
  const student1Page = await student1Context.newPage();
  const student2Page = await student2Context.newPage();

  async function loginPage(page: typeof tutorPage, email: string, password: string) {
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Login" }).click();
  }

  await loginPage(tutorPage, tutor.email, tutor.password);
  await expect(tutorPage).toHaveURL(/dashboard/);
  await loginPage(student1Page, student1.email, student1.password);
  await expect(student1Page).toHaveURL(/student\/dashboard/);
  await loginPage(student2Page, student2.email, student2.password);
  await expect(student2Page).toHaveURL(/student\/dashboard/);
  const tokens = await Promise.all([tutorPage, student1Page, student2Page].map((page) => page.evaluate(() => localStorage.getItem("tutorflow_token"))));
  expect(new Set(tokens).size).toBe(3);

  await tutorPage.goto(`/sessions/${session1.id}`);
  await tutorPage.getByTestId("start-btn").click();
  await expect(tutorPage.locator(".status-in_progress")).toContainText("In Progress");
  await student1Page.goto("/student/dashboard");
  await student1Page.reload();
  await expect(student1Page.locator("body")).toContainText("In Progress");
  await expect(student1Page.locator("body")).not.toContainText("Student Two");
  await student2Page.goto("/student/dashboard");
  await expect(student2Page.locator("body")).not.toContainText("In Progress");
  await expect(student2Page.locator("body")).not.toContainText("Student One");

  await Promise.all([tutorContext.close(), student1Context.close(), student2Context.close()]);
});
