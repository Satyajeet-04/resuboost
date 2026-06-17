from services.groq_client import GroqClient
import json

ATS_SYSTEM = """You are an ATS compatibility expert. Analyze resumes against specific ATS platform requirements and scoring patterns."""

ATS_PLATFORMS = {
    "greenhouse": "Greenhouse uses human-centric scorecards with minimal auto-rejection. It ranks candidates by keyword relevance (30%), experience alignment (25%), skills match (20%), and education (15%). It parses resumes into structured fields and lets recruiters search by any field. Completing optional fields (like LinkedIn, cover letter, salary) increases ranking by 2.8x.",
    "workday": "Workday uses OCR + NLP parsing. Knockout questions are the #1 rejection cause. It ranks by keyword density in specific sections (40%), experience years (25%), skills certifications (20%), education (10%), and format parseability (5%). Prefers single-column, standard headers, no tables.",
    "lever": "Lever uses tag-based scoring. Recruiters assign tags to candidates. It ranks by custom scoring rubrics set by each company. Keyword matching in the first 200 words matters more. Resume parse quality affects search ranking.",
    "icims": "iCIMS uses semantic matching rather than keyword counting. It understands synonyms and related skills (e.g., 'React' matches 'React.js'). Uses NLP embeddings to match resume content to job requirements holistically.",
    "taleo": "Taleo uses traditional keyword filtering. It parses resumes and scores based on exact keyword matches. Section headers must be standard (Experience, Education, Skills). Uses weighted keyword scoring where some keywords count more than others."
}

def build_ats_prompt(resume: str, jd: str, platform: str) -> str:
    platform_info = ATS_PLATFORMS.get(platform, ATS_PLATFORMS["greenhouse"])
    return f"""Simulate how this resume would be scored by the following ATS platform.

ATS PLATFORM: {platform.upper()}

HOW THIS ATS WORKS:
{platform_info}

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return JSON:
{{
  "platform": "{platform}",
  "overall_score": 68,
  "parseability": {{
    "score": 80,
    "issues": ["Uses two-column layout which this ATS may mis-parse"]
  }},
  "keyword_match": {{
    "score": 60,
    "matched": ["Python", "React", "AWS"],
    "missing": ["Kubernetes", "Docker", "Terraform"]
  }},
  "section_compatibility": {{
    "clean": true,
    "issues": [],
    "warning": "Consider renaming 'Work History' to 'Experience'"
  }},
  "specific_feedback": "This ATS would parse your resume well but you'd score low on keyword match",
  "action_items": ["Add 'Kubernetes' to Skills section", "..."]
}}

Rules:
- Parseability score: how well this ATS can extract text (tables? columns? standard headers?)
- Keyword match: what the ATS finds vs misses
- Section compatibility: does this ATS recognize your section headers?
- Specific feedback must reference the actual ATS platform behavior
- 3-5 actionable action_items unique to this ATS"""

class ATSBreakdown:
    def __init__(self, platform: str = "greenhouse"):
        self.client = GroqClient(task_type="ats_breakdown")
        self.platform = platform

    def analyze(self, resume: str, job_description: str) -> dict:
        prompt = build_ats_prompt(resume, job_description, self.platform)
        raw = self.client.generate(prompt, system_instruction=ATS_SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "overall_score" not in result or "platform" not in result:
            raise ValueError("Response missing 'overall_score' or 'platform' fields")
        return result
