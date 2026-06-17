from services.groq_client import GroqClient
import json

COVER_LETTER_SYSTEM = """You are a professional cover letter writer. Write tailored, compelling cover letters that highlight relevant experience and address job requirements. Use a professional but engaging tone. Keep each paragraph focused and impactful."""

def build_cover_letter_prompt(resume: str, jd: str) -> str:
    return f"""Write a professional cover letter tailored to this job description.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return JSON:
{{
  "cover_letter": "full cover letter text as a single string with \\n line breaks",
  "subject_line": "email subject line for the application",
  "key_points": ["point1", "point2", "point3"]
}}

Rules:
- Address the hiring manager by role (Dear Hiring Manager)
- Highlight 2-3 specific achievements from the resume that match the JD
- Mention why the candidate is excited about this specific role
- Keep it to 3-4 paragraphs
- Professional but not overly formal tone"""

class CoverLetterGenerator:
    def __init__(self):
        self.client = GroqClient(task_type="cover_letter")

    def generate(self, resume: str, job_description: str) -> dict:
        prompt = build_cover_letter_prompt(resume, job_description)
        raw = self.client.generate(prompt, system_instruction=COVER_LETTER_SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "cover_letter" not in result:
            raise ValueError("Response missing 'cover_letter' field")
        return result
