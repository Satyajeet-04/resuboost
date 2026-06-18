"""Token-optimized recruiter search simulator."""
from services.groq_client import GroqClient
import json

PROMPT_TEMPLATE = """Role: {role}

Generate 8 Boolean search queries a recruiter would use. For each, say if this resume matches.

RESUME: {resume}

Respond JSON:
{{
  "queries": [{{"query": "boolean", "match": bool, "why": "..."}}],
  "match_rate": <0-100>
}}
Rules: 4 should match, 4 shouldn't. Vary specificity."""

class Simulator:
    def __init__(self):
        self.client = GroqClient(task_type="simulate")

    def simulate(self, resume: str, role: str) -> dict:
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, role=role))
        result = json.loads(raw)
        if not isinstance(result, dict) or "queries" not in result or "match_rate" not in result:
            raise ValueError("Invalid simulate response")
        return result
