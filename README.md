# TutorFlow

A small full-stack app for 1:1 online tutors: role-based tutor/student accounts, a
strictly server-enforced session lifecycle (`Scheduled` → `In Progress` → `Completed` →
`AI Reviewed`), and AI-generated session plans/summaries grounded in each student's real
profile and history.

Built for a take-home task with a 100-point rubric weighted toward data modelling, AI
prompt quality, and server-side rule enforcement over frontend polish.

## Stack

- **Backend:** FastAPI + SQLAlchemy + Alembic, PostgreSQL
- **Frontend:** React + TypeScript + Vite
- **AI:** Gemini 2.5 Flash-Lite (Google AI Studio, free tier)
- **Auth:** JWT, bcrypt-hashed passwords
- **Hosting:** Render (backend web service + frontend static site), DB on Supabase/Neon

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

## Live deployment

- **URL:** _add once deployed_
- **GitHub:** _this repo_
- **Test credentials:** _add tutor and student test logins here before submission_

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
   - **STUDENT** endpoints: View own sessions and profile, update session notes (while in progress)
   - No student can access another student's data, even by guessing session IDs—all queries are filtered by JWT claims server-side, never by client-supplied parameters

### Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/auth/register-tutor` | ❌ | Register a new tutor account |
| POST | `/auth/login` | ❌ | Log in and receive JWT token |
| GET | `/auth/me` | ✅ | Get current user info (id, email, role) |

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
| **IN_PROGRESS** | Complete session, update notes | Update notes | COMPLETED | Session is actively happening |
| **COMPLETED** | Trigger AI review | View only | AI_REVIEWED | Session finished, tutor added notes/homework |
| **AI_REVIEWED** | View summary | View summary | ❌ (read-only) | AI summary generated, session archived |

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

## AI Integration (Phase 5)

TutorFlow uses **Gemini 2.5 Flash-Lite** to generate context-aware session plans and summaries grounded in real student data.

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

Student: {student_name}, level: {skill_level}
Learning goals: {learning_goals}
Preferences: {preferences}

Most recent prior session (if any):
- Notes: {previous_notes}
- Homework assigned: {previous_homework}
- AI summary of that session: {previous_ai_summary}

Today's session: subject/duration as given by tutor: {duration_minutes} minutes.

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

Generates a structured summary for the student's record based on:
- Session notes written by tutor
- Homework assigned
- Student's profile

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

Student: {student_name}, level: {skill_level}, goals: {learning_goals}
This session's tutor notes: {notes}
Homework assigned: {homework}

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
