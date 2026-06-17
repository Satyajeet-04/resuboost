from services.groq_client import GroqClient
import json
from config import settings

SYSTEM_INSTRUCTION = """You are a senior technical recruiter at a top tech company.
You review thousands of resumes against job descriptions.
Your analysis is precise, honest, and actionable."""

def build_analyze_prompt(resume: str, jd: str) -> str:
    return f"""Compare this RESUME against the JOB DESCRIPTION.
Identify specific missing skills, qualifications, or experiences that would reduce interview chances.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return JSON:
{{
  "gaps": [
    {{
      "skill": "exact skill or qualification name",
      "importance": "high" | "medium" | "low",
      "reason": "why this matters for this specific role, referencing the JD"
    }}
  ],
  "match_score": <integer 0-100 indicating overall resume-JD fit>
}}

Rules:
- Only flag genuine gaps (do not hallucinate requirements).
- "high" = explicitly required in JD and completely absent
- "medium" = mentioned in JD but weak in resume
- "low" = nice-to-have in JD, not present
- Maximum 12 gaps.
- If resume has no gaps for this JD, return empty gaps array and score 100."""

class GapAnalyzer:
    def __init__(self):
        self.client = GroqClient(task_type="analyze")

    def analyze(self, resume: str, jd: str) -> dict:
        prompt = build_analyze_prompt(resume, jd)
        raw = self.client.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "gaps" not in result or "match_score" not in result:
            raise ValueError("Gemini response missing 'gaps' or 'match_score' fields")
        return result
