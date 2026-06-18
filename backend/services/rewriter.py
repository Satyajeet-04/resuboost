"""Token-optimized bullet rewriter. Uses STAR format."""
from services.groq_client import GroqClient
import json

PROMPT_TEMPLATE = """Rewrite experience bullets to highlight: {skill}

RESUME: {resume}
CONTEXT: {context}

Respond JSON:
{{
  "original": ["bullet 1", ...],
  "rewritten": ["bullet 1 (STAR)", ...],
  "explanation": "brief"
}}
Rules: factual only, use STAR, max 6 bullets, measurable outcomes when available."""

class Rewriter:
    def __init__(self):
        self.client = GroqClient(task_type="rewrite")

    def rewrite(self, resume: str, skill: str, context: str = "") -> dict:
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, skill=skill, context=context))
        result = json.loads(raw)
        if not isinstance(result, dict) or "original" not in result or "rewritten" not in result:
            raise ValueError("Invalid rewrite response")
        return result
