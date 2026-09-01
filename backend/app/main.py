"""FastAPI application entry point for TutorFlow backend."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db
from app.api import auth, students, sessions

# Initialize FastAPI app
app = FastAPI(
    title="TutorFlow API",
    description="Backend for TutorFlow tutoring platform",
    version="0.1.0",
)

# Configure CORS for local Vite and localhost development
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
for origin in ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"):
    if origin not in cors_origins:
        cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(db=Depends(get_db)):
    """
    Health check endpoint that verifies backend and database connectivity.
    
    Returns:
        dict: {"status": "ok", "db": "connected"} on success
    
    Returns 503 if database is unreachable.
    """
    try:
        # Perform a trivial DB query to verify connectivity
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {
            "status": "error",
            "db": "disconnected",
            "error": str(e),
        }, 503


# Include routers
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(sessions.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
