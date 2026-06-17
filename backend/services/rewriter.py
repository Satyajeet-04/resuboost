from services.gemini_client import GeminiClient
import json

def build_rewrite_prompt(resume: str, skill: str, context: str = "") -> str:
    return f"""Rewrite the work experience bullets in this RESUME to better highlight: {skill}

RESUME:
{resume}

CONTEXT ABOUT THE TARGET ROLE:
{context}

Return JSON:
{{
  "original": ["bullet 1", "bullet 2", ...],
  "rewritten": ["rewritten bullet 1", "rewritten bullet 2", ...],
  "explanation": "Brief explanation of how the rewrite adds this skill"
}}

Rules:
- Keep all facts truthful. Do NOT fabricate experience.
- Use STAR format (Situation, Task, Action, Result) where possible.
- Include measurable outcomes when available.
- Preserve the original resume's tone and format.
- Maximum 6 bullets."""

class Rewriter:
    def __init__(self):
        self.client = GeminiClient()

    def rewrite(self, resume: str, skill: str, context: str = "") -> dict:
        prompt = build_rewrite_prompt(resume, skill, context)
        raw = self.client.generate(prompt)
        result = json.loads(raw)
        return result
