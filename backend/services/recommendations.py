"""Smart recommendations engine — actionable insights beyond gap detection."""
from services.groq_client import GroqClient
import json

SYSTEM = """You are a senior career coach and hiring strategist. Your recommendations are specific, actionable, and prioritize quick wins that maximize interview chances."""

PROMPT_TEMPLATE = """Analyze this resume against the job description and create a prioritized action plan.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return JSON:
{{
  "recommendations": [
    {{
      "category": "upskill|rewrite|practice|network",
      "priority": "critical|high|medium|low",
      "title": "short actionable title",
      "description": "detailed why and what to do",
      "actionable_steps": ["step1", "step2"],
      "courses": [{{"platform": "Coursera|Udemy|free", "title": "course name", "url": "url or empty", "reason": "why this specific course"}}],
      "micropractices": [{{"task": "what to do", "time_minutes": 15, "difficulty": "easy|medium|hard", "impact": "high|medium"}}],
      "estimated_time": "30 mins|2 hours|1 week",
      "roi": "quick_win|high_impact|long_term"
    }}
  ],
  "quick_wins": ["top 3 things to do TODAY"],
  "estimated_prep_time": "total estimated prep time",
  "focus_area": "the single most important thing to improve"
}}

Rules:
- 5-8 recommendations, mix of categories
- At least 2 quick_wins (can do today, <30 min each)
- Each recommendation must have actionable_steps
- Courses: real platforms only, give search query in url if no specific URL
- Micropractices: small specific exercises
- BE SPECIFIC — reference actual resume content and JD requirements
- No generic advice. Every recommendation ties to the candidate's specific resume."""


class RecommendationEngine:
    def __init__(self):
        self.client = GroqClient(task_type="recommend")

    def recommend(self, resume: str, job_description: str) -> dict:
        max_len = 4000
        safe_resume = resume[:max_len]
        safe_jd = job_description[:max_len]
        prompt = PROMPT_TEMPLATE.format(resume=safe_resume, jd=safe_jd)
        raw = self.client.generate(prompt, SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict) or "recommendations" not in result:
            raise ValueError("Invalid recommendation response")
        if not result.get("quick_wins"):
            result["quick_wins"] = [r["title"] for r in result["recommendations"][:3]]
        return result
