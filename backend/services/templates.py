"""Resume templates engine — 5 ATS-friendly templates + AI recommender."""
from services.groq_client import GroqClient
import json

# 5 curated ATS-friendly resume templates
TEMPLATES = [
    {
        "id": "ats-classic",
        "name": "ATS Classic",
        "description": "Clean single-column layout with traditional section headers. Highest ATS parseability. Best for corporate roles.",
        "preview": "1-column | Header: Name, Phone, Email, LinkedIn | Sections: Summary, Skills, Experience, Education, Certifications",
        "best_for": ["Corporate jobs", "Finance", "Consulting", "Traditional industries"],
        "ats_score": 98,
    },
    {
        "id": "modern-engineering",
        "name": "Modern Engineering",
        "description": "Skills-first layout with technical proficiency bars. Light accent color header for visual distinction while staying ATS-safe.",
        "preview": "1-column | Colored header bar | Sections: Technical Skills, Experience, Projects, Education, Achievements",
        "best_for": ["Software Engineering", "DevOps", "Data Science", "Tech roles"],
        "ats_score": 92,
    },
    {
        "id": "impact-driven",
        "name": "Impact Driven",
        "description": "Achievement-focused layout with prominent metrics section. Emphasizes quantified results and career progression.",
        "preview": "1-column | Impact metrics bar at top | Sections: Career Highlights, Experience (with KPIs), Skills, Education",
        "best_for": ["Senior roles", "Management", "Sales", "Roles requiring measurable impact"],
        "ats_score": 88,
    },
    {
        "id": "academic-research",
        "name": "Academic & Research",
        "description": "Publication and research-focused layout. Includes sections for papers, talks, grants, and teaching experience.",
        "preview": "1-column | Sections: Research Interests, Publications, Teaching, Grants, Skills, Education",
        "best_for": ["PhD applications", "Research positions", "Postdocs", "Academic roles"],
        "ats_score": 85,
    },
    {
        "id": "startup-generalist",
        "name": "Startup Generalist",
        "description": "Versatile layout that highlights breadth of skills. Combines experience, projects, and side work in a narrative flow.",
        "preview": "1-column | Narrative summary | Sections: Core Competencies, Experience, Side Projects, Skills, Education",
        "best_for": ["Startups", "Product Management", "Early-stage companies", "Generalist roles"],
        "ats_score": 90,
    },
]


class TemplateEngine:
    def __init__(self):
        self.templates = TEMPLATES

    def get_all(self) -> list[dict]:
        return self.templates

    def recommend(self, resume: str, job_description: str = "") -> dict:
        """AI-powered template recommendation based on resume content and JD."""
        if not job_description:
            job_description = "General role (no specific JD provided)"
        system = "You are a resume format expert. Match resumes to the best ATS-friendly template."
        prompt = f"""Given this resume and job description, recommend the best template from the options below.

RESUME:
{resume[:3000]}

JD:
{job_description[:2000]}

TEMPLATES:
{json.dumps(self.templates, indent=2)}

Return JSON:
{{
  "recommended": [<TEMPLATE OBJECTS in priority order, max 3>],
  "reasoning": "why these templates fit this resume/JD, referencing specific content"
}}
Select templates based on: industry fit, experience level, content style (academic vs impact vs technical), and ATS score."""

        client = GroqClient(task_type="templates")
        raw = client.generate(prompt, system)
        result = json.loads(raw)
        if not isinstance(result, dict) or "recommended" not in result:
            raise ValueError("Invalid template recommendation response")
        return result
