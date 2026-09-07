"""Seed the deployed API with the two TutorFlow demo accounts and sessions."""

import argparse
import os
from datetime import datetime, timedelta, timezone

import httpx


TUTOR_EMAIL = os.getenv("DEMO_TUTOR_EMAIL", "demo.tutor@tutorflow.dev")
TUTOR_PASSWORD = os.getenv("DEMO_TUTOR_PASSWORD", "TutorFlowDemo123!")
STUDENT_EMAIL = os.getenv("DEMO_STUDENT_EMAIL", "demo.student@tutorflow.dev")
STUDENT_PASSWORD = os.getenv("DEMO_STUDENT_PASSWORD", "TutorFlowStudent123!")


def request(client: httpx.Client, method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.request(method, path, headers=headers, **kwargs)
    if response.is_error:
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text}")
    return response.json()


def login(client: httpx.Client, email: str, password: str) -> str:
    result = request(client, "POST", "/auth/login", json={"email": email, "password": password})
    return result["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("API_URL", "http://localhost:8000"))
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    with httpx.Client(base_url=base_url, timeout=90) as client:
        try:
            tutor_token = login(client, TUTOR_EMAIL, TUTOR_PASSWORD)
        except RuntimeError:
            request(client, "POST", "/auth/register-tutor", json={"email": TUTOR_EMAIL, "password": TUTOR_PASSWORD})
            tutor_token = login(client, TUTOR_EMAIL, TUTOR_PASSWORD)

        students = request(client, "GET", "/students", tutor_token)
        if students:
            raise RuntimeError("The tutor already has students; refusing to create data outside the two-account demo.")

        student = request(
            client,
            "POST",
            "/students",
            tutor_token,
            json={
                "name": "Demo Student",
                "email": STUDENT_EMAIL,
                "initial_password": STUDENT_PASSWORD,
                "learning_goals": "Build confidence with Python fundamentals and problem solving.",
                "skill_level": "Intermediate",
                "preferences": "Short explanations followed by hands-on practice.",
            },
        )

        now = datetime.now(timezone.utc).replace(microsecond=0)
        completed_start = now - timedelta(minutes=5)
        completed_end = now + timedelta(minutes=55)
        completed = request(
            client,
            "POST",
            "/sessions",
            tutor_token,
            json={
                "student_id": student["user_id"],
                "start_time": completed_start.isoformat().replace("+00:00", "Z"),
                "end_time": completed_end.isoformat().replace("+00:00", "Z"),
            },
        )
        request(client, "POST", f"/sessions/{completed['id']}/ai-plan", tutor_token, json={"duration_minutes": 60})
        request(client, "PATCH", f"/sessions/{completed['id']}/start", tutor_token, json={})
        request(
            client,
            "PATCH",
            f"/sessions/{completed['id']}/complete",
            tutor_token,
            json={
                "notes": "Reviewed Python functions, parameter passing, and debugging a small input-validation exercise.",
                "homework": "Write three functions that validate and transform a short list of user inputs.",
            },
        )
        request(client, "PATCH", f"/sessions/{completed['id']}/trigger-ai-review", tutor_token, json={})

        upcoming_start = now + timedelta(days=1)
        upcoming_end = upcoming_start + timedelta(hours=1)
        upcoming = request(
            client,
            "POST",
            "/sessions",
            tutor_token,
            json={
                "student_id": student["user_id"],
                "start_time": upcoming_start.isoformat().replace("+00:00", "Z"),
                "end_time": upcoming_end.isoformat().replace("+00:00", "Z"),
            },
        )

    print(f"Tutor: {TUTOR_EMAIL} / {TUTOR_PASSWORD}")
    print(f"Student: {STUDENT_EMAIL} / {STUDENT_PASSWORD}")
    print(f"AI-reviewed session: {completed['id']}")
    print(f"Upcoming session: {upcoming['id']}")


if __name__ == "__main__":
    main()