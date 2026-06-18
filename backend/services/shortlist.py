from services.groq_client import GroqClient
import json

class ShortlistEngine:
    def __init__(self):
        self.max_iterations = 4
        self.target_score = 85

    def shortlist(self, resume: str, job_description: str, aggressive: bool = False):
        iteration_log = []
        current_resume = resume
        original_resume = resume

        for i in range(self.max_iterations):
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

            gaps_for_rewrite = weaknesses[:5] if weaknesses else ["general alignment"]
            current_resume = self._aggressive_rewrite(
                current_resume, original_resume, job_description, gaps_for_rewrite, aggressive, i == self.max_iterations - 1
            )

        final_score_result = self._score_resume(current_resume, job_description)
        final_score = final_score_result.get("overall_score", 0)

        return {
            "resume": current_resume,
            "original_resume": original_resume,
            "final_score": final_score,
            "shortlist_verified": final_score >= self.target_score,
            "iterations": iteration_log,
            "changes_summary": self._build_changes_summary(iteration_log, original_resume, current_resume)
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

    def _aggressive_rewrite(self, resume: str, original: str, jd: str, gaps: list, aggressive: bool, final_pass: bool) -> str:
        groq = GroqClient(task_type="shortlist")

        intensity = "MAXIMUM" if aggressive or final_pass else "HIGH"
        prompt = f"""You are an expert ATS resume tailor. This resume MUST be substantially rewritten — not just keyword-padded.

Job Description:
{jd[:3000]}

Original resume (DO NOT keep this exact wording):
{original[:3000]}

Current version (may already be partially rewritten):
{resume[:3000]}

Target gaps to address:
{', '.join(gaps)}

Rewrite intensity: {intensity}

YOUR TASK: Rewrite the ENTIRE resume so it is clearly DIFFERENT from the original while keeping ALL facts accurate.

MANDATORY CHANGES:
1. **Restructure every bullet point** — change sentence structure, verb choices, and emphasis. Example: "Built a full-stack app with React" → "Architected and deployed a full-stack web application leveraging React.js for dynamic frontend interfaces"
2. **Add a professional summary** (3-4 sentences) that directly mirrors the JD's language
3. **Categorize skills** into groups matching the JD requirements (e.g., Languages, Frameworks, Cloud, Databases)
4. **Reframe project descriptions** to highlight JD-relevant outcomes (performance, scale, impact)
5. Use STRONGER action verbs: Architected, Designed, Implemented, Optimized, Deployed, Engineered, Developed, Built
6. Every bullet should be noticeably different from the original in wording

RULES:
- KEEP factual accuracy: same company names, dates, degree names, certifications
- NEVER add degrees, employment, or credentials that don't exist
- Format: single-column, standard sections (Summary, Skills, Experience, Projects, Education)
- NO tables, columns, graphics, or markdown formatting

Return JSON:
{{
  "full_resume": "the COMPLETE rewritten resume text — must be substantially different wording from original",
  "changes_summary": "list specific rewording changes made: e.g., 'Added professional summary mirroring JD language', 'Rewrote project bullet to emphasize scalable architecture'"
}}"""
        system = "You are an expert ATS resume optimization assistant. You MUST substantially reword the resume while keeping facts accurate. Same facts, completely different presentation."

        text = groq.generate(prompt, system)
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result.get("full_resume", resume)
        except (json.JSONDecodeError, ValueError):
            pass

        return resume

    def _build_changes_summary(self, iteration_log: list, original: str, final: str) -> str:
        lines = []
        for entry in iteration_log:
            lines.append(f"Iteration {entry['iteration']}: Score {entry['score']}/100 ({entry['remaining_weaknesses']} weaknesses remaining)")
        last = iteration_log[-1]
        if last['score'] >= self.target_score:
            lines.append(f"✅ Target reached: {last['score']}/100")
        else:
            lines.append(f"⚠️ Final score: {last['score']}/100 (target: {self.target_score}/100)")

        # Show structural change indicators
        orig_lines = original.strip().split('\n')
        final_lines = final.strip().split('\n')
        lines.append(f"\n📊 Change Stats:")
        lines.append(f"  Original: {len(orig_lines)} lines, {len(original)} chars")
        lines.append(f"  Shortlist: {len(final_lines)} lines, {len(final)} chars")
        lines.append(f"  Difference: {abs(len(final_lines) - len(orig_lines))} line change")

        if len(original) > 0:
            change_pct = int(abs(len(final) - len(original)) / len(original) * 100)
            lines.append(f"  Content change: ~{change_pct}% different from original")

        return "\n".join(lines)
