from services.groq_client import GroqClient
import json

INTERVIEW_SYSTEM = """You are a technical interview coach. Generate realistic interview questions based on resume gaps and job requirements. Focus on helping the candidate prepare for what they'll actually be asked."""

def build_questions_prompt(resume: str, jd: str, gaps: list) -> str:
    gaps_text = "\n".join([f"- {g}" for g in gaps]) if gaps else "No specific gaps identified"
    return f"""Generate likely interview questions for this candidate applying to this role.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

IDENTIFIED GAPS:
{gaps_text}

Return JSON:
{{
  "questions": [
    {{
      "question": "Walk me through a time you had to...",
      "category": "behavioral",
      "difficulty": "medium",
      "why_asked": "This tests your experience with X, which is a key requirement",
      "preparation_tip": "Use the STAR method: describe the Situation, Task, Action, and Result"
    }}
  ],
  "total_questions": 8,
  "categories_covered": ["technical", "behavioral", "system_design"]
}}

Generate 8-10 questions across these categories:
1. technical — specific skills from the JD
2. behavioral — STAR-format questions
3. gap_focused — questions about missing skills (to assess learning ability)
4. experience_deep_dive — questions about listed projects/roles

Rules:
- At least 2 questions should target the identified gaps
- For gap-focused questions, include preparation tips on how to answer despite the gap
- Difficulty levels: easy, medium, hard
- Realistic questions a real interviewer would ask"""

class InterviewQuestionGenerator:
    def __init__(self):
        self.client = GroqClient(task_type="interview_questions")

    def generate(self, resume: str, job_description: str, gaps: list = None) -> dict:
        if gaps is None:
            gaps = []
        prompt = build_questions_prompt(resume, job_description, gaps)
        raw = self.client.generate(prompt, system_instruction=INTERVIEW_SYSTEM)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "questions" not in result:
            raise ValueError("Response missing 'questions' field")
        return result
