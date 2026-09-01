"""FastAPI application entry point for TutorFlow backend."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db
from app.api import auth

# Initialize FastAPI app
app = FastAPI(
    title="TutorFlow API",
    description="Backend for TutorFlow tutoring platform",
    version="0.1.0",
)

# Configure CORS
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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


# Future route includes will go here
# from app.api import sessions, students
# app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
# app.include_router(students.router, prefix="/students", tags=["students"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
