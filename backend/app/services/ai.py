"""AI service for Gemini-powered session planning and summarization."""

import json
from typing import Optional
import logging

from google import genai

from app.core.config import settings
from app.models import Session, StudentProfile

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class AIServiceRateLimitError(AIServiceError):
    """Raised when Gemini rate limit is hit (429)."""
    pass


class AIServiceTimeoutError(AIServiceError):
    """Raised when Gemini call times out."""
    pass


def _call_gemini(prompt: str, max_retries: int = 1) -> str:
    """
    Call Gemini API with retry logic.
    
    Args:
        prompt: The prompt to send to Gemini
        max_retries: Number of retries on transient errors
        
    Returns:
        Raw response text from Gemini
        
    Raises:
        AIServiceRateLimitError: If rate limited (429)
        AIServiceTimeoutError: If timeout
        AIServiceError: For other API errors
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    attempt = 0
    while attempt <= max_retries:
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit errors
            if "429" in error_str or "rate" in error_str:
                raise AIServiceRateLimitError(f"Gemini rate limit exceeded: {e}")
            
            # Check for timeout errors
            if "timeout" in error_str or "deadline" in error_str:
                if attempt < max_retries:
                    attempt += 1
                    logger.warning(f"Gemini timeout, retrying (attempt {attempt}/{max_retries})")
                    continue
                raise AIServiceTimeoutError(f"Gemini timeout after {max_retries + 1} attempts: {e}")
            
            # Other errors
            if attempt < max_retries:
                attempt += 1
                logger.warning(f"Gemini error, retrying (attempt {attempt}/{max_retries}): {e}")
                continue
            
            raise AIServiceError(f"Gemini API error: {e}")
    
    raise AIServiceError("Unexpected error in Gemini call")


def generate_session_plan(
    student_profile: StudentProfile,
    previous_session: Optional[Session],
    duration_minutes: Optional[int] = None,
) -> dict:
    """
    Generate a session plan using Gemini.
    
    Builds a prompt with student profile and prior session context (if any),
    sends it to Gemini, and returns the parsed JSON response.
    
    Args:
        student_profile: StudentProfile instance
        previous_session: Previous COMPLETED-or-later session (if any)
        duration_minutes: Duration for today's session (optional)
        
    Returns:
        Parsed JSON dict with keys: warm_up, main_focus, practice_activities, check_for_understanding
        
    Raises:
        AIServiceError: On Gemini API failures
    """
    # Build prior session context
    if previous_session:
        prior_context = f"""Most recent prior session (if any):
- Notes: {previous_session.notes or "(no notes recorded)"}
- Homework assigned: {previous_session.homework or "(no homework assigned)"}
- AI summary of that session: {previous_session.ai_summary or "(no AI summary available)"}"""
    else:
        prior_context = """Most recent prior session (if any):
There is no prior session record for this student. This is their first session."""

    # Build the prompt
    prompt = f"""You are an assistant helping a tutor prepare for a 1:1 session.

Student: {student_profile.user_id}, level: {student_profile.skill_level or "(not specified)"}
Learning goals: {student_profile.learning_goals or "(not specified)"}
Preferences: {student_profile.preferences or "(not specified)"}

{prior_context}

Today's session: duration: {duration_minutes or "unknown"} minutes.

Produce a session plan as JSON with keys: 
  "warm_up" (string), "main_focus" (string, tied to a specific weakness above if one exists), 
  "practice_activities" (array of strings), "check_for_understanding" (string).
Do not invent facts about the student not present above. If there is no prior session, 
say so explicitly and build a plan from the stated goals and level only.
Return JSON only, no prose outside the JSON object."""

    # Call Gemini
    response_text = _call_gemini(prompt)
    
    # Parse JSON response
    try:
        # Try to extract JSON if it's wrapped in markdown code blocks
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
        
        plan_data = json.loads(json_str)
        return plan_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini plan response as JSON: {response_text}")
        raise AIServiceError(f"Failed to parse Gemini response as JSON: {e}")


def generate_session_summary(
    student_profile: StudentProfile,
    session: Session,
    previous_session: Optional[Session] = None,
) -> dict:
    """
    Generate a session summary using Gemini.
    
    Analyzes the completed session's notes and homework, grounded in student profile,
    and returns a structured JSON summary.
    
    Args:
        student_profile: StudentProfile instance
        session: Completed Session instance with notes and homework
        
    Returns:
        Parsed JSON dict with keys: summary, strengths, areas_to_improve, recommended_next_topic
        
    Raises:
        AIServiceError: On Gemini API failures
    """
    if previous_session:
        prior_context = f"""Most recent prior session (if any):
- Notes: {previous_session.notes or "(no notes recorded)"}
- Homework assigned: {previous_session.homework or "(no homework assigned)"}
- AI summary of that session: {previous_session.ai_summary or "(no AI summary available)"}"""
    else:
        prior_context = """Most recent prior session (if any):
There is no prior session record for this student."""

    # Build the prompt
    prompt = f"""You are summarizing a completed 1:1 tutoring session for the student's ongoing record.

Student: {student_profile.user_id}, level: {student_profile.skill_level or "(not specified)"}, goals: {student_profile.learning_goals or "(not specified)"}
{prior_context}

This session's tutor notes: {session.notes or "(no notes recorded)"}
Homework assigned: {session.homework or "(no homework assigned)"}

Produce JSON with keys:
  "summary" (2-3 sentences, plain language, written for the student to read),
  "strengths" (array of strings, grounded only in the notes above),
  "areas_to_improve" (array of strings, grounded only in the notes above),
  "recommended_next_topic" (string, one specific suggestion).
Base every claim strictly on the notes provided — do not fabricate skills or struggles 
not mentioned. Return JSON only, no prose outside the JSON object."""

    # Call Gemini
    response_text = _call_gemini(prompt)
    
    # Parse JSON response
    try:
        # Try to extract JSON if it's wrapped in markdown code blocks
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
        
        summary_data = json.loads(json_str)
        return summary_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini summary response as JSON: {response_text}")
        raise AIServiceError(f"Failed to parse Gemini response as JSON: {e}")
