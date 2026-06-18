"""Token-optimized keyword analyzer."""
from services.groq_client import GroqClient
import json

SYSTEM = "You are an ATS keyword optimization expert."

PROMPT_TEMPLATE = """Extract important keywords from JD and check resume coverage.

RESUME:
{resume}

JD:
{jd}

Respond JSON:
{{
  "keywords": [{{"keyword": "name", "in_resume": bool, "importance": "high|medium|low", "category": "skill|tool|domain|soft_skill|cert", "suggestion": "where to add if missing"}}],
  "stats": {{"total_keywords": int, "matched": int, "missing": int, "coverage_pct": float}},
  "top_missing": ["kw1", "kw2"],
  "recommendation": "summary"
}}
Rules: 15-25 keywords. High=required/multiple mentions. For missing ones, suggest WHERE to add (Skills section, Experience bullet, Summary)."""

class KeywordAnalyzer:
    def __init__(self):
        self.client = GroqClient(task_type="keywords")

    def analyze(self, resume: str, job_description: str) -> dict:
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, jd=job_description), SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict) or "keywords" not in result or "stats" not in result:
            raise ValueError("Invalid keywords response")
        return result
