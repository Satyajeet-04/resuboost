"""Token-optimized interview question generator."""
from services.groq_client import GroqClient
import json

SYSTEM = "You are a technical interview coach. Realistic questions based on gaps and job requirements."

PROMPT_TEMPLATE = """Generate interview questions.

RESUME:
{resume}

JD:
{jd}

GAPS:
{gaps}

Respond JSON:
{{
  "questions": [{{"question": "...", "category": "technical|behavioral|gap_focused|experience_deep_dive", "difficulty": "easy|medium|hard", "why_asked": "...", "preparation_tip": "..."}}],
  "total_questions": int,
  "categories_covered": ["cat1", ...]
}}
Rules: 8-10 questions. At least 2 targeting identified gaps. For gap questions, include prep tips on how to answer despite gap."""

class InterviewQuestionGenerator:
    def __init__(self):
        self.client = GroqClient(task_type="interview_questions")

    def generate(self, resume: str, job_description: str, gaps: list = None) -> dict:
        gaps_text = "\n".join([f"- {g}" for g in (gaps or [])]) or "No specific gaps"
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, jd=job_description, gaps=gaps_text), SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict) or "questions" not in result:
            raise ValueError("Invalid interview_questions response")
        return result
