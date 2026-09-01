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

## Database schema, session state machine, and AI prompts

_To be documented here once implemented — see the build plan for the required sections._

## Known limitations

_To be documented once implemented._
