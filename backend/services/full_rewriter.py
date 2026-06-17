from services.gemini_client import GeminiClient
import json

def build_full_rewrite_prompt(resume: str, gaps: list[str], jd: str) -> str:
    gap_list = ", ".join(gaps)
    return f"""You are an expert resume writer. Rewrite the COMPLETE resume below to address ALL these missing skills: {gap_list}

JOB DESCRIPTION (target role):
{jd}

CURRENT RESUME:
{resume}

Return JSON:
{{
  "full_resume": "The completely rewritten resume with all gaps addressed. Include ALL sections (Summary, Experience, Education, Skills, Projects, etc.) from the original resume, rewritten to highlight the missing skills where truthful.",
  "changes_summary": "Bullet points explaining what was changed and why"
}}

RULES (CRITICAL):
- Do NOT fabricate experience. Only add skills in ways that are truthful based on the resume.
- For skills that truly don't exist in the candidate's background, add them in a Skills section or suggest learning them.
- Preserve the original resume's sections and overall structure.
- Use action verbs and STAR format for experience bullets.
- Maximum 5000 characters total.
- Keep the rewrite natural and human-readable — not keyword-stuffed."""

class FullRewriter:
    def __init__(self):
        self.client = GeminiClient()

    def full_rewrite(self, resume: str, gaps: list[str], jd: str) -> dict:
        prompt = build_full_rewrite_prompt(resume, gaps, jd)
        raw = self.client.generate(prompt)
        result = json.loads(raw)
        return result
