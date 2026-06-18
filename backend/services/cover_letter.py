"""Token-optimized cover letter generator."""
from services.groq_client import GroqClient
import json

SYSTEM = "You are a professional cover letter writer. Be tailored, compelling, and concise."

PROMPT_TEMPLATE = """Write a tailored cover letter.

RESUME:
{resume}

JD:
{jd}

Respond JSON:
{{
  "cover_letter": "full letter with \\n line breaks",
  "subject_line": "email subject line",
  "key_points": ["pt1", "pt2", "pt3"]
}}
Rules: Dear Hiring Manager, highlight 2-3 specific achievements matching JD, mention why excited about role, 3-4 paragraphs, professional tone."""

class CoverLetterGenerator:
    def __init__(self):
        self.client = GroqClient(task_type="cover_letter")

    def generate(self, resume: str, job_description: str) -> dict:
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, jd=job_description), SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict) or "cover_letter" not in result:
            raise ValueError("Invalid cover_letter response")
        return result
