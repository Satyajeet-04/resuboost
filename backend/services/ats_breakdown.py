"""Token-optimized ATS platform breakdown."""
from services.groq_client import GroqClient
import json

SYSTEM = "You are an ATS compatibility expert."

ATS_PLATFORMS = {
    "greenhouse": "Human-centric scorecards. Ranks by: keyword relevance (30%), experience alignment (25%), skills match (20%), education (15%). No auto-rejection.",
    "workday": "OCR+NLP parsing. Knockout questions #1 rejection cause. Ranks by: keyword density (40%), experience (25%), skills (20%), education (10%), format (5%). Prefers single-column, standard headers, no tables.",
    "lever": "Tag-based scoring. Keyword matching in first 200 words matters most. Resume parse quality affects search ranking.",
    "icims": "Semantic matching (understands synonyms like React ~ React.js). NLP embeddings for holistic matching.",
    "taleo": "Exact keyword filtering. Standard section headers required (Experience, Education, Skills). Weighted keyword scoring."
}

PROMPT_TEMPLATE = """Simulate ATS scoring for this resume.

ATS: {platform.upper()}
HOW IT WORKS: {ats_info}

RESUME: {resume}
JD: {jd}

Respond JSON:
{{
  "platform": "{platform}",
  "overall_score": <0-100>,
  "parseability": {{"score": <0-100>, "issues": ["..."]}},
  "keyword_match": {{"score": <0-100>, "matched": ["kw1"], "missing": ["kw2"]}},
  "section_compatibility": {{"clean": bool, "issues": [], "warning": "..."}},
  "specific_feedback": "...",
  "action_items": ["item1", "item2", "item3"]
}}
Rules: Parseability = text extraction quality. Keyword = ATS finds vs misses. Section = header recognition. 3-5 actionable items specific to this ATS."""

class ATSBreakdown:
    def __init__(self, platform: str = "greenhouse"):
        self.client = GroqClient(task_type="ats_breakdown")
        self.platform = platform

    def analyze(self, resume: str, job_description: str) -> dict:
        ats_info = ATS_PLATFORMS.get(self.platform, ATS_PLATFORMS["greenhouse"])
        raw = self.client.generate(
            PROMPT_TEMPLATE.format(platform=self.platform, ats_info=ats_info, resume=resume, jd=job_description),
            SYSTEM
        )
        result = json.loads(raw)
        if not isinstance(result, dict) or "overall_score" not in result or "platform" not in result:
            raise ValueError("Invalid ats_breakdown response")
        return result
