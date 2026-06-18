from services.groq_client import GroqClient
import json

class ShortlistEngine:
    def __init__(self):
        self.max_iterations = 4
        self.target_score = 85

    def shortlist(self, resume: str, job_description: str, aggressive: bool = False):
        iteration_log = []
        current_resume = resume

        for i in range(self.max_iterations):
            # Score current resume via direct Groq call (resume_scorer)
            score_result = self._score_resume(current_resume, job_description)
            score_val = score_result.get("overall_score", 0)
            weaknesses = score_result.get("weaknesses", [])

            iteration_log.append({
                "iteration": i + 1,
                "score": score_val,
                "remaining_weaknesses": len(weaknesses)
            })

            if score_val >= self.target_score:
                break

            # Aggressive rewrite targeting weaknesses
            gaps_for_rewrite = weaknesses[:5] if weaknesses else ["general alignment"]
            current_resume = self._aggressive_rewrite(
                current_resume, job_description, gaps_for_rewrite, aggressive, i == self.max_iterations - 1
            )

        # Final score
        final_score_result = self._score_resume(current_resume, job_description)
        final_score = final_score_result.get("overall_score", 0)

        return {
            "resume": current_resume,
            "final_score": final_score,
            "shortlist_verified": final_score >= self.target_score,
            "iterations": iteration_log,
            "changes_summary": self._build_changes_summary(iteration_log)
        }

    def _score_resume(self, resume: str, jd: str) -> dict:
        groq = GroqClient(task_type="resume_scorer")
        prompt = f"""You are an ATS resume scoring expert. Score this resume against the job description.

Job Description:
{jd[:3000]}

Resume:
{resume[:3000]}

Score from 0-100 based on: keyword match, experience alignment, skills coverage, education fit, and format/readability.

Return JSON:
{{
  "overall_score": int,
  "strengths": ["strength1", ...],
  "weaknesses": ["weakness1", ...]
}}"""
        system = "You are an ATS scoring expert. Return only valid JSON."
        text = groq.generate(prompt, system)
        try:
            result = json.loads(text)
            if not isinstance(result, dict):
                return {"overall_score": 0, "strengths": [], "weaknesses": []}
            return result
        except (json.JSONDecodeError, ValueError):
            return {"overall_score": 0, "strengths": [], "weaknesses": []}

    def _aggressive_rewrite(self, resume: str, jd: str, gaps: list, aggressive: bool, final_pass: bool) -> str:
        groq = GroqClient(task_type="shortlist")

        intensity = "MAXIMUM" if aggressive or final_pass else "HIGH"
        prompt = f"""You are an expert ATS resume tailor. Rewrite this resume to PASS ATS SCREENING with near-perfect keyword match.

Job Description:
{jd[:3000]}

Resume to optimize:
{resume[:3000]}

Target gaps to address:
{', '.join(gaps)}

Rewrite intensity: {intensity}

RULES (follow exactly):
1. Include EVERY relevant keyword and phrase from the job description naturally in the resume
2. Rewrite ALL bullet points to use JD language - reframe existing experience
3. Add a professional summary that mirrors the JD's exact language
4. Skills section must contain ALL matching keywords from the JD (categorized)
5. Projects section: reframe to highlight JD-relevant technologies and outcomes
6. For skills not directly present: use "Familiarity with", "Exposure to", "Coursework in", "Working knowledge of" — ONLY if truthfully applicable
7. NEVER add degrees, certifications, companies, or employment dates that don't exist
8. Keep ALL factual information (names, dates, education) ACCURATE
9. Format: single-column, standard sections (Summary, Skills, Experience, Projects, Education), NO tables/columns/graphics
10. Each bullet must be achievement-oriented with metrics where possible

Return JSON:
{{
  "full_resume": "the complete rewritten resume text",
  "changes_summary": "brief description of key changes made"
}}"""
        system = "You are an expert ATS resume optimization assistant. Rewrite resumes to maximize ATS keyword match while keeping all information truthful and accurate."

        text = groq.generate(prompt, system)
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result.get("full_resume", resume)
        except (json.JSONDecodeError, ValueError):
            pass

        # If JSON parsing fails, return original
        return resume

    def _build_changes_summary(self, iteration_log: list) -> str:
        if not iteration_log:
            return "No changes needed"
        lines = []
        for entry in iteration_log:
            lines.append(f"Iteration {entry['iteration']}: Score {entry['score']}/100 ({entry['remaining_weaknesses']} weaknesses remaining)")
        last = iteration_log[-1]
        if last['score'] >= self.target_score:
            lines.append(f"✅ Target reached: {last['score']}/100")
        else:
            lines.append(f"⚠️ Final score: {last['score']}/100 (target: {self.target_score}/100)")
        return "\n".join(lines)
