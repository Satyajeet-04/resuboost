from services.groq_client import GroqClient
import json

KEYWORDS_SYSTEM = """You are an ATS keyword optimization expert. Analyze job descriptions and resumes to identify critical keywords and assess coverage."""

def build_keywords_prompt(resume: str, jd: str) -> str:
    return f"""Extract the most important keywords from the job description and check which ones appear in the resume.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return JSON:
{{
  "keywords": [
    {{
      "keyword": "cloud computing",
      "in_resume": true,
      "importance": "high",
      "category": "skill",
      "suggestion": "Already present — ensure it's prominent"
    }}
  ],
  "stats": {{
    "total_keywords": 25,
    "matched": 15,
    "missing": 10,
    "coverage_pct": 60
  }},
  "top_missing": ["keyword1", "keyword2", "keyword3"],
  "recommendation": "Summary of which keywords to add and where"
}}

Rules:
- Extract 15-25 keywords total (mix of skills, tools, soft skills, domain terms)
- Categories: skill, tool, domain, soft_skill, certification
- Importance: high (required/mentioned multiple times), medium (nice-to-have), low (minor mention)
- If in_resume is false, suggestion should say WHERE to add it (Skills section, Experience bullet, Summary)
- Focus on keywords that would affect ATS ranking"""

class KeywordAnalyzer:
    def __init__(self):
        self.client = GroqClient(task_type="keywords")

    def analyze(self, resume: str, job_description: str) -> dict:
        prompt = build_keywords_prompt(resume, job_description)
        raw = self.client.generate(prompt, system_instruction=KEYWORDS_SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "keywords" not in result or "stats" not in result:
            raise ValueError("Response missing 'keywords' or 'stats' fields")
        return result
