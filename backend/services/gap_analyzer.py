"""Token-optimized gap analyzer. Compares resume to JD, identifies missing skills."""
from services.groq_client import GroqClient
import json

SYSTEM = "You are a senior tech recruiter. Be precise, honest, actionable."

PROMPT_TEMPLATE = """Resume vs Job Description — find gaps that reduce interview chances.

RESUME:
{resume}

JD:
{jd}

Respond JSON:
{{
  "gaps": [{{"skill": "name", "importance": "high|medium|low", "reason": "why for this role"}}],
  "match_score": <0-100>
}}
Rules: max 12 gaps. high=missing required, medium=weak, low=nice-to-have. Empty gaps + 100 if no gaps."""

class GapAnalyzer:
    def __init__(self):
        self.client = GroqClient(task_type="analyze")

    def analyze(self, resume: str, jd: str) -> dict:
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, jd=jd), SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict) or "gaps" not in result or "match_score" not in result:
            raise ValueError("Invalid analyze response")
        return result
