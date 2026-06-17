from services.groq_client import GroqClient
import json

SCORER_SYSTEM = """You are a resume evaluation expert. Score resumes across multiple dimensions to assess overall quality and job fit. Be specific and actionable."""

def build_scorer_prompt(resume: str, jd: str) -> str:
    return f"""Evaluate this resume against the job description and score it across multiple dimensions.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return JSON:
{{
  "overall_score": 72,
  "scores": [
    {{
      "category": "Keyword Coverage",
      "score": 65,
      "max_score": 100,
      "reason": "Missing key terms: Kubernetes, Docker, CI/CD",
      "tip": "Add DevOps keywords to Skills section"
    }}
  ],
  "strengths": ["Strong project descriptions with measurable outcomes"],
  "weaknesses": ["No certifications listed"],
  "priority_fixes": ["Add cloud computing keywords", "Quantify more achievements"]
}}

Score categories (evaluate ALL 7):
1. "Keyword Coverage" — Does resume include JD keywords?
2. "Experience Relevance" — Is past experience relevant to this role?
3. "Achievement Impact" — Are achievements quantified?
4. "Format & Readability" — Clear sections, consistent formatting?
5. "Skills Presentation" — Skills clearly listed and relevant?
6. "Education & Certifications" — Relevant degrees, certs, training?
7. "Overall Fit" — Holistic match for this specific role

Rules:
- Each score 0-100
- overall_score is weighted average
- Be honest, don't inflate scores
- priority_fixes should be 3-5 actionable items"""

class ResumeScorer:
    def __init__(self):
        self.client = GroqClient(task_type="resume_scorer")

    def score(self, resume: str, job_description: str) -> dict:
        prompt = build_scorer_prompt(resume, job_description)
        raw = self.client.generate(prompt, system_instruction=SCORER_SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "overall_score" not in result or "scores" not in result:
            raise ValueError("Response missing 'overall_score' or 'scores' fields")
        return result
