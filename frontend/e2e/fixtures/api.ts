import type { APIRequestContext } from "@playwright/test";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type Credentials = { email: string; password: string };
export type Student = { id: string; user_id: string; name?: string; email?: string };
export type Session = {
  id: string;
  start_time: string;
  end_time: string;
  status: string;
};

async function json<T>(response: Awaited<ReturnType<APIRequestContext["fetch"]>>): Promise<T> {
  if (!response.ok()) {
    throw new Error(`${response.status()}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export async function registerTutor(request: APIRequestContext): Promise<Credentials> {
  const credentials = {
    email: `tutor-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "TutorPass123!",
  };
  await json(await request.post(`${API_URL}/auth/register-tutor`, { data: credentials }));
  return credentials;
}

export async function login(request: APIRequestContext, credentials: Credentials): Promise<string> {
  const response = await json<{ access_token: string }>(
    await request.post(`${API_URL}/auth/login`, { data: credentials }),
  );
  return response.access_token;
}

export async function createStudent(
  request: APIRequestContext,
  tutorToken: string,
  overrides: Partial<Credentials & { name: string; learning_goals: string }> = {},
): Promise<Credentials & Student> {
  const credentials = {
    name: overrides.name ?? `Student ${Date.now()}`,
    email: overrides.email ?? `student-e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    initial_password: overrides.password ?? "StudentPass123!",
    learning_goals: overrides.learning_goals ?? "Playwright testing",
    skill_level: "Beginner",
    preferences: "Evenings",
  };
  const student = await json<Student>(
    await request.post(`${API_URL}/students`, {
      data: credentials,
      headers: { Authorization: `Bearer ${tutorToken}` },
    }),
  );
  return { ...credentials, password: credentials.initial_password, ...student };
}

export async function createSession(
  request: APIRequestContext,
  tutorToken: string,
  studentId: string,
  start: Date,
  end: Date,
): Promise<Session> {
  return json<Session>(
    await request.post(`${API_URL}/sessions`, {
      data: {
        student_id: studentId,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
      },
      headers: { Authorization: `Bearer ${tutorToken}` },
    }),
  );
}

export async function apiRequest(
  request: APIRequestContext,
  token: string,
  path: string,
  method: "PATCH" | "DELETE",
  data?: unknown,
) {
  return request.fetch(`${API_URL}${path}`, {
    method,
    data,
    headers: { Authorization: `Bearer ${token}` },
  });
}
