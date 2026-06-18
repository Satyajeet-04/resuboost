"""Token-optimized resume scorer."""
from services.groq_client import GroqClient
import json

SYSTEM = "You are a resume evaluation expert. Be specific and actionable."

PROMPT_TEMPLATE = """Score this resume against the JD across 7 dimensions (0-100 each, weighted overall).

RESUME:
{resume}

JD:
{jd}

Categories: Keyword Coverage, Experience Relevance, Achievement Impact, Format & Readability, Skills Presentation, Education & Certifications, Overall Fit.

Respond JSON:
{{
  "overall_score": <0-100>,
  "scores": [{{"category": "name", "score": int, "max_score": 100, "reason": "...", "tip": "..."}}],
  "strengths": ["s1", ...],
  "weaknesses": ["w1", ...],
  "priority_fixes": ["fix1", "fix2", "fix3"]
}}
Rules: Honest scoring. Priority fixes: 3-5 actionable items."""

class ResumeScorer:
    def __init__(self):
        self.client = GroqClient(task_type="resume_scorer")

    def score(self, resume: str, job_description: str) -> dict:
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, jd=job_description), SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict) or "overall_score" not in result or "scores" not in result:
            raise ValueError("Invalid score response")
        return result
