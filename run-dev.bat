@echo off
set "ROOT=%~dp0"

start "TutorFlow Backend" /D "%ROOT%backend" cmd /k ""%ROOT%.venv\Scripts\python.exe" -m uvicorn app.main:app --reload"
start "TutorFlow Frontend" /D "%ROOT%frontend" cmd /k "npm run dev"