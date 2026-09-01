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

## Database schema, session state machine, and AI prompts

_To be documented here once implemented — see the build plan for the required sections._

## Known limitations

_To be documented once implemented._
