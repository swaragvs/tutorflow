# TutorFlow

A small full-stack app for 1:1 online tutors: role-based tutor/student accounts, a
strictly server-enforced session lifecycle (`Scheduled` → `In Progress` → `Completed` →
`AI Reviewed`), and tutor-facing AI session plans and summaries grounded in each student's
stored profile and session context.

TutorFlow is a focused workspace for 1:1 tutors to schedule sessions, record notes and
homework, and review AI-generated preparation and summaries. Tutors manage the lifecycle;
students can see only their own upcoming sessions, past notes, and homework.

## Stack

- **Backend:** FastAPI + SQLAlchemy + Alembic, PostgreSQL
- **Frontend:** React + TypeScript + Vite
- **AI:** Gemini via Google AI Studio (`GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`)
- **Auth:** JWT, bcrypt-hashed passwords
- **Hosting:** Render backend, Vercel frontend, Supabase PostgreSQL
- **External services:** Google AI Studio/Gemini and Supabase PostgreSQL are intended to use
  their free tiers; account plan and quota status must be confirmed in their dashboards.

## Repo layout

```
tutorflow/
  backend/    FastAPI app, SQLAlchemy models, Alembic migrations
  frontend/   React + TS + Vite app
```

## Local setup

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET, GEMINI_API_KEY
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_URL if backend isn't on localhost:8000
npm run dev
```

## Live URL, GitHub, and demo credentials

- **Frontend:** https://tutorflow-vs.vercel.app
- **Backend:** https://tutorflow-api-yax3.onrender.com
- **GitHub:** https://github.com/swaragvs/tutorflow
- **Tutor:** `demo.tutor@tutorflow.dev` / `TutorFlowDemo123!`
- **Student:** `demo.student@tutorflow.dev` / `TutorFlowStudent123!`

The first backend request may take up to a minute because the free-tier Render service
sleeps after inactivity.

## Architecture

The Vercel-hosted React/TypeScript/Vite client calls a FastAPI service on Render. FastAPI
uses SQLAlchemy and Alembic against Supabase PostgreSQL, while Gemini generates structured
session plans and summaries. This stack keeps the client typed and fast to iterate, puts
authorization and lifecycle rules on the server, and fits the free-tier deployment model.

## Deployment

1. Create a Supabase project and set its PostgreSQL connection string as `DATABASE_URL`.
2. Connect the GitHub repository to Render as a web service with root directory `backend/`.
  The checked-in `render.yaml` contains the build, start, health-check, and secret-variable
  declarations. Set `DATABASE_URL`, `JWT_SECRET`, `GEMINI_API_KEY`, and other values in the
  Render dashboard; never commit them.
3. Run `alembic upgrade head` from `backend/` against the production database.
4. Import `frontend/` into Vercel as a Vite project and set `VITE_API_URL` to the Render URL.
5. Set Render's `CORS_ORIGINS` to the exact Vercel origin, then redeploy the backend.
6. Seed the production API once, after migrations, with:

  ```bash
  cd backend
  python scripts/seed_demo.py --base-url https://tutorflow-api-yax3.onrender.com
  ```

  Set `DEMO_TUTOR_PASSWORD` and `DEMO_STUDENT_PASSWORD` in the shell before running it.
  The script creates exactly one tutor, one student, one AI-reviewed session, and one
  upcoming scheduled session, then prints the credentials and session IDs.

7. Cold-load the Vercel URL in an incognito window and verify tutor login, logout, student
  login, ownership filtering, tutor-side AI-reviewed content, and the upcoming session.

## Implementation status and remaining checks

Implemented in the repository:

- Tutors create and link student accounts through `POST /students`; students do not self-register.
- JWT authentication, bcrypt password hashing, role checks, ownership filtering, and the
  four-state session lifecycle are enforced by the backend.
- The overlap check uses an application-level query for a clear conflict message and a
  PostgreSQL exclusion constraint for the same tutor's time ranges, with the
  `(tutor_id, start_time)` index supporting lookup.
- AI plans and summaries use the student profile, the current session record, and the most
  recent prior completed/reviewed session's notes, homework, and AI summary when one exists.
  AI fields are returned to tutors, not students.
- The deployment configuration, live URLs, and demo credentials are recorded above. The
  latest local access-scope changes still require a Git push and fresh Render/Vercel deploy
  before they are present in production.

Remaining or intentionally not guaranteed:

- The PostgreSQL exclusion constraint closes the same-tutor concurrent overlap race for the
  deployed PostgreSQL database. The application-level fallback remains the behavior used by
  SQLite-based tests.
- The repository cannot prove the billing tier or remaining quota of external accounts. Confirm
  Supabase's free-plan status and Google AI Studio quota in their dashboards before submission.
  Render's free-tier cold-start behavior is documented below.
- The API stores naive database datetimes and the frontend interprets naive API timestamps as
  UTC for display; an explicit timezone-aware database column/serialization remains a future
  hardening improvement.
- After the latest changes are deployed, rerun the production smoke test and verify both demo
  logins and the tutor/student AI-field boundary against the live URLs.

## Requirements alignment

Implemented:

- Two roles are implemented: tutors create student accounts, schedule sessions, record notes,
  and manage the lifecycle; students can access only their own upcoming sessions, past notes,
  and homework.
- The lifecycle is `SCHEDULED -> IN_PROGRESS -> COMPLETED -> AI_REVIEWED`. The backend stores
  it as an enum and enforces transitions through the central
  `backend/app/services/session_state.py` service, rather than relying on hidden UI buttons.
- Completed sessions are locked for normal edits. The explicit AI-review transition remains
  available to the tutor.
- Tutor and student demo credentials, the GitHub repository, and deployed frontend/backend
  URLs are listed above.

Not fully guaranteed or still requiring confirmation:

- Same-tutor double booking is rejected by an application-level overlap query and protected in
  PostgreSQL by an exclusion constraint on the tutor and session time range. The migration
  requires the `btree_gist` extension and must be applied before relying on the database guard.
- The plan and summary prompts use the student profile, current session data, and the most
  recent prior completed/reviewed session context when one exists.
- The latest local access-scope changes are not yet represented in production until they are
  pushed and both services redeploy. Production smoke verification must be repeated afterward.
- The repository identifies Google AI Studio and Supabase as the external AI/database
  services, but it cannot verify their free-tier billing status or remaining quota.

## Authentication & Authorization

TutorFlow uses **JWT-based authentication** with role-based access control (RBAC).

### How it works

1. **Registration**: Tutors can register via `POST /auth/register-tutor` with email and password.
   - Password is hashed with bcrypt before storage (never stored in plain text)
   - User role is automatically set to `TUTOR`
   - Response includes user ID, email, and role

2. **Login**: Both tutors and students log in via `POST /auth/login` with email and password.
   - Server verifies password against bcrypt hash
   - Returns a JWT access token with 24-hour expiry
   - Token contains user ID and role as claims

3. **Authorization**: All protected endpoints require the `Authorization` header with format:
   ```
   Authorization: Bearer <jwt_token>
   ```
   - Server decodes and validates token (signature, expiry, claims)
   - Returns 401 if token is missing, invalid, or expired
   - Returns 403 if user's role doesn't match endpoint requirements

4. **Role-based Access**: 
   - **TUTOR** endpoints: Create students, schedule sessions, manage session state, trigger AI reviews
  - **STUDENT** access: View only their own sessions, notes, and homework; AI plan and summary
    fields are omitted from student session-detail responses
   - No student can access another student's data, even by guessing session IDs—all queries are filtered by JWT claims server-side, never by client-supplied parameters

### Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/auth/register-tutor` | ❌ | Register a new tutor account |
| POST | `/auth/login` | ❌ | Log in and receive JWT token |
| GET | `/auth/me` | ✅ | Get current user info (id, email, role) |
| POST | `/students` | Tutor | Create and link a student account |
| GET | `/students` | Tutor | List the tutor's linked students |
| GET | `/students/{id}` | Tutor | Retrieve an owned student profile |
| PATCH | `/students/{id}` | Tutor | Update an owned student's profile |

### Example usage

```bash
# Register
curl -X POST http://localhost:8000/auth/register-tutor \
  -H "Content-Type: application/json" \
  -d '{"email":"tutor@example.com","password":"SecurePassword123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tutor@example.com","password":"SecurePassword123"}'

# Response: {"access_token":"eyJ0eXAiOiJKV1QiLCJhbGc...", "token_type":"bearer"}

# Use token to access protected endpoint
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Response: {"id":"550e8400-e29b-41d4-a716-446655440000","email":"tutor@example.com","role":"TUTOR"}
```

## Session Lifecycle & State Machine

TutorFlow enforces a **strictly linear session state machine** to prevent invalid operations:

```
SCHEDULED → IN_PROGRESS → COMPLETED → AI_REVIEWED
```

| State | Tutor Can | Student Can | Transitions To | Notes |
|-------|-----------|-------------|---|---------|
| **SCHEDULED** | Start session | View only | IN_PROGRESS | Session is booked but not started |
| **IN_PROGRESS** | Complete session, update notes | View notes/homework | COMPLETED | Session is actively happening |
| **COMPLETED** | Trigger AI review | View only | AI_REVIEWED | Session finished, tutor added notes/homework |
| **AI_REVIEWED** | View plan and summary | View notes and homework | ❌ (read-only) | AI artifacts remain tutor-only; the session is archived |

### Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/sessions` | Tutor | Create new SCHEDULED session |
| GET | `/sessions` | Both | List own sessions (tutor sees all, student sees own) |
| GET | `/sessions/{id}` | Both | Retrieve single session (owner only) |
| PATCH | `/sessions/{id}/start` | Tutor | Transition SCHEDULED → IN_PROGRESS |
| PATCH | `/sessions/{id}/complete` | Tutor | Add notes/homework, transition IN_PROGRESS → COMPLETED |
| PATCH | `/sessions/{id}/notes` | Tutor | Update notes while IN_PROGRESS |
| POST | `/sessions/{id}/ai-plan` | Tutor | Generate AI plan for SCHEDULED session |
| PATCH | `/sessions/{id}/trigger-ai-review` | Tutor | Call AI service, generate summary, transition COMPLETED → AI_REVIEWED |

## AI Integration

TutorFlow uses the configured Gemini model (default: `gemini-3.5-flash-lite`) to generate
context-aware tutor-facing session plans and summaries grounded in real student data.

### AI Functions

#### 1. Generate Session Plan

**Endpoint**: `POST /sessions/{session_id}/ai-plan`  
**Authorization**: Tutor only  
**Valid state**: SCHEDULED only

Generates a structured lesson plan based on:
- Student's profile (skill level, learning goals, preferences)
- Previous session notes/homework (if any) for continuity
- Session duration

**Example request**:
```json
{
  "duration_minutes": 60
}
```

**Example response**:
```json
{
  "status": "SCHEDULED",
  "ai_plan": {
    "warm_up": "5-minute review of previous homework on functions",
    "main_focus": "Understanding Python decorators for advanced function manipulation",
    "practice_activities": [
      "Live coding example of decorator syntax",
      "Student implements custom decorator for timing functions",
      "Debugging decorator errors"
    ],
    "check_for_understanding": "Have student explain what a decorator does and when to use one"
  }
}
```

**Prompt template** (interpolates real database values):
```
You are an assistant helping a tutor prepare for a 1:1 session.

Student: {student_profile.user_id}, level: {student_profile.skill_level or "(not specified)"}
Learning goals: {student_profile.learning_goals or "(not specified)"}
Preferences: {student_profile.preferences or "(not specified)"}

Most recent prior session (if any):
- Notes: {previous_notes}
- Homework assigned: {previous_homework}
- AI summary of that session: {previous_ai_summary}

Today's session: duration: {duration_minutes or "unknown"} minutes.

Produce a session plan as JSON with keys: 
  "warm_up" (string), "main_focus" (string, tied to a specific weakness above if one exists), 
  "practice_activities" (array of strings), "check_for_understanding" (string).
Do not invent facts about the student not present above. If there is no prior session, 
say so explicitly and build a plan from the stated goals and level only.
Return JSON only, no prose outside the JSON object.
```

#### 2. Generate Session Summary

**Endpoint**: `PATCH /sessions/{session_id}/trigger-ai-review`  
**Authorization**: Tutor only  
**Valid state**: COMPLETED only

Generates a structured summary for the tutor's session record based on:
- Session notes written by tutor
- Homework assigned
- Student's profile
- Most recent prior session notes, homework, and AI summary when available

AI plans and summaries are tutor-only artifacts. Student session responses omit these
fields; students receive their own session status, notes, and homework instead.

**Example request**:
```json
{}
```

**Example response**:
```json
{
  "status": "AI_REVIEWED",
  "ai_summary": {
    "summary": "Excellent session! You mastered the basics of functions and even tried a few advanced patterns. We covered function definition, argument passing, and return values with several hands-on examples.",
    "strengths": [
      "Quickly grasped variable scope",
      "Asked clarifying questions about edge cases",
      "Successfully debugged own code"
    ],
    "areas_to_improve": [
      "Could name variables more descriptively",
      "Try docstrings for function documentation"
    ],
    "recommended_next_topic": "Lambda functions and functional programming patterns"
  }
}
```

**Prompt template** (interpolates real database values):
```
You are summarizing a completed 1:1 tutoring session for the student's ongoing record.

Student: {student_profile.user_id}, level: {student_profile.skill_level or "(not specified)"}, goals: {student_profile.learning_goals or "(not specified)"}
Most recent prior session (if any):
- Notes: {previous_notes}
- Homework assigned: {previous_homework}
- AI summary of that session: {previous_ai_summary}

This session's tutor notes: {session.notes or "(no notes recorded)"}
Homework assigned: {session.homework or "(no homework assigned)"}

Produce JSON with keys:
  "summary" (2-3 sentences, plain language, written for the student to read),
  "strengths" (array of strings, grounded only in the notes above),
  "areas_to_improve" (array of strings, grounded only in the notes above),
  "recommended_next_topic" (string, one specific suggestion).
Base every claim strictly on the notes provided — do not fabricate skills or struggles 
not mentioned. Return JSON only, no prose outside the JSON object.
```

### Error Handling

- **429 (Rate Limited)**: Gemini API hit rate limit → returns 502 with "temporarily unavailable"
- **Timeout**: Connection timeout on retry → returns 502 with "temporarily unavailable"
- **Other errors**: Gemini API errors → returns 502 with error message

All errors are logged for debugging. Sessions remain in their current state if AI call fails.

## Database Schema

The status field is a native PostgreSQL enum so invalid lifecycle states cannot enter the
database accidentally. The `(tutor_id, start_time)` index supports the overlap query used
when a tutor schedules or reschedules a session, keeping that check efficient as data grows.

### Users
- `id` (UUID, primary key)
- `email` (string, unique)
- `password_hash` (bcrypt)
- `role` (enum: TUTOR, STUDENT)
- `created_at` (timestamp)

### Student Profiles
- `id` (UUID, primary key)
- `user_id` (UUID, FK→users, unique)
- `tutor_id` (UUID, FK→users, restricts cascade deletes)
- `learning_goals` (text, optional)
- `skill_level` (text, optional)
- `preferences` (text, optional)
- `created_at` (timestamp)

### Sessions
- `id` (UUID, primary key)
- `tutor_id` (UUID, FK→users, restricts cascade deletes)
- `student_id` (UUID, FK→users, restricts cascade deletes)
- `start_time` (datetime)
- `end_time` (datetime)
- `status` (enum: SCHEDULED, IN_PROGRESS, COMPLETED, AI_REVIEWED)
- `notes` (text, optional)
- `homework` (text, optional)
- `ai_plan` (JSON string, optional)
- `ai_summary` (JSON string, optional)
- `created_at` (timestamp)
- `updated_at` (timestamp)
- **Index**: `(tutor_id, start_time)` for overlap checking

## Known limitations

- The overlap check is an application-level query before insert and has a theoretical
  race-condition window between checking and inserting; PostgreSQL deployments use the
  `sessions_no_tutor_time_overlap` exclusion constraint from migration `0003` to close it.
- The free-tier Render backend may sleep after inactivity; the first load may take up to a
  minute while the service wakes.
- There is no admin role, live video/audio, or chat. These were deliberately scoped out.
- Tutor registration does not currently collect a display name, so tutor-facing labels may
  fall back to the account email or a placeholder.

## How to run locally

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows; use source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env  # fill in DATABASE_URL, JWT_SECRET, and GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
copy .env.example .env  # set VITE_API_URL if the backend is not on localhost:8000
npm run dev
```
