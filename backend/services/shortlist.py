from services.groq_client import GroqClient
import json
import re

def _robust_json_parse(text: str):
    """Parse JSON from AI response, handling markdown fences and extra text."""
    # Strip markdown fences if present
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find JSON object in text
    obj_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass
    # Try array
    arr_match = re.search(r'\[.*?\]', text, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass
    return None

class ShortlistEngine:
    def __init__(self):
        self.max_iterations = 3
        self.target_score = 88

    def shortlist(self, resume: str, job_description: str, aggressive: bool = False):
        iteration_log = []
        current_resume = resume
        original_resume = resume

        # Extract JD keywords upfront for injection
        jd_keywords = self._extract_jd_keywords(job_description)

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

            gaps_for_rewrite = weaknesses[:6] if weaknesses else ["keyword alignment"]
            current_resume = self._keyword_inject_rewrite(
                current_resume, original_resume, job_description,
                jd_keywords, gaps_for_rewrite,
                aggressive or i == self.max_iterations - 1
            )

        final_score_result = self._score_resume(current_resume, job_description)
        final_score = final_score_result.get("overall_score", 0)

        return {
            "resume": current_resume,
            "original_resume": original_resume,
            "final_score": final_score,
            "shortlist_verified": final_score >= self.target_score,
            "iterations": iteration_log,
            "changes_summary": self._build_changes_summary(iteration_log, original_resume, current_resume),
            "jd_keywords": jd_keywords,
        }

    # ------------------------------------------------------------------
    # Extract keywords from JD
    # ------------------------------------------------------------------
    def _extract_jd_keywords(self, jd: str) -> list:
        """Extract tech skills, tools, and concepts from the job description."""
        groq = GroqClient(task_type="keywords")
        prompt = f"""Extract ALL technical skills, tools, frameworks, platforms, and concepts from this job description.

Job Description:
{jd[:3000]}

Return as a JSON array of strings. Include EVERY skill/tool/concept mentioned.
Example: ["Python", "AWS", "Microservices", "System Design", "CI/CD", "Docker", "Kubernetes", "Agile"]"""
        system = "You are a JD keyword extractor. Return ONLY a valid JSON array of strings. No markdown."
        text = groq.generate(prompt, system)
        result = _robust_json_parse(text)
        if isinstance(result, list):
            return result
        # Fallback: simple extraction
        tech_words = re.findall(r'\b[A-Z][A-Za-z0-9+#.]+(?:\s*[A-Z][A-Za-z0-9+#.]+)*\b', jd)
        return list(set(w for w in tech_words if len(w) > 1))[:20]

    # ------------------------------------------------------------------
    # Score resume
    # ------------------------------------------------------------------
    def _score_resume(self, resume: str, jd: str) -> dict:
        groq = GroqClient(task_type="resume_scorer")
        prompt = f"""Score this resume against the job description (0-100). Be strict.

JD:
{jd[:3000]}

Resume:
{resume[:3000]}

Return JSON:
{{{{
  "overall_score": int,
  "strengths": ["s1", ...],
  "weaknesses": ["w1", ...]
}}}}"""
        system = "ATS scoring expert. Return ONLY valid JSON."
        text = groq.generate(prompt, system)
        result = _robust_json_parse(text)
        if isinstance(result, dict):
            return result
        return {"overall_score": 0, "strengths": [], "weaknesses": []}

    # ------------------------------------------------------------------
    # Aggressive rewrite with keyword injection
    # ------------------------------------------------------------------
    def _keyword_inject_rewrite(self, resume: str, original: str, jd: str,
                                 jd_keywords: list, gaps: list, final_pass: bool) -> str:
        groq = GroqClient(task_type="shortlist")

        missing_kws = [k for k in jd_keywords if k.lower() not in resume.lower()]

        prompt = f"""You are an expert ATS resume optimizer. Your job: REWRITE this resume to score HIGH on ATS filters.

JOB DESCRIPTION (TARGET):
{jd[:3500]}

ORIGINAL RESUME:
{original[:3000]}

CURRENT VERSION:
{resume[:3000]}

JD KEYWORDS NOT IN RESUME (INJECT THESE):
{', '.join(missing_kws[:15])}

GAPS TO FIX:
{', '.join(gaps)}

{'⚠️ FINAL PASS - MAKE EVERY EFFORT' if final_pass else 'IMPROVE THIS RESUME'}

INSTRUCTIONS (CRITICAL):
1. **INJECT ALL missing JD keywords** into the Skills section. Add them as relevant skills.
2. **Add JD keywords into experience bullets** naturally: "Leveraged AWS cloud infrastructure for scalable deployments with CI/CD pipelines"
3. **Rewrite every bullet** using JD-specific language. If JD asks for "distributed systems" and resume says "built a web app", rewrite to "Designed and implemented a distributed web application architecture"
4. **Add a professional summary** (3-5 sentences) that mirrors JD language and keywords
5. **Categorize skills** into groups: Languages, Cloud & DevOps, Databases, Frameworks, Tools
6. **Use stronger action verbs**: Architected, Engineered, Designed, Deployed, Optimized, Implemented, Led, Built

RULES:
- KEEP: real company names, dates, degrees, certifications, job titles
- YOU CAN ADD: any skill/keyword from the JD into skills section and as context in experience
- NEVER add: fake degrees, fake employment, fake company names
- Format: standard sections (Summary, Skills, Experience, Projects, Education)
- NO tables, columns, graphics, markdown

Return JSON:
{{{{
  "full_resume": "COMPLETE rewritten resume — MUST include JD keywords naturally",
  "changes_summary": "list what changed: e.g., 'Added AWS, Microservices, Docker skills', 'Rewrote experience bullet with distributed systems language'"
}}}}"""
        system = "You are an ATS optimization engine. Inject missing JD keywords into the resume naturally. Rewrite every section for maximum ATS match while keeping facts true."

        text = groq.generate(prompt, system)
        result = _robust_json_parse(text)
        if isinstance(result, dict):
            rewritten = result.get("full_resume", resume)
            # Ensure at least SOME keywords made it
            for kw in jd_keywords[:10]:
                if kw.lower() not in rewritten.lower():
                    rewritten = self._inject_keyword(rewritten, kw)
            return rewritten

        # Fallback: inject keywords minimally
        result = resume
        for kw in jd_keywords[:10]:
            if kw.lower() not in result.lower():
                result = self._inject_keyword(result, kw)
        return result

    # ------------------------------------------------------------------
    # Fallback keyword injector
    # ------------------------------------------------------------------
    def _inject_keyword(self, resume: str, keyword: str) -> str:
        """Inject a missing keyword into the skills section or summary."""
        if keyword.lower() in resume.lower():
            return resume
        # Try to add to Skills section
        skills_match = re.search(r'(?i)(SKILLS|TECHNICAL SKILLS|TECHNOLOGIES|EXPERTISE)\s*\n', resume)
        if skills_match:
            pos = skills_match.end()
            # Find end of skills section (next section header or end)
            next_section = re.search(r'\n(?=[A-Z][A-Za-z\s]+:\s*\n|\n[A-Z][A-Za-z\s]+\n[-=]+\n)', resume[pos:])
            end_pos = pos + (next_section.start() if next_section else len(resume[pos:]))
            # Add keyword at end of skills
            resume = resume[:end_pos].rstrip() + f", {keyword}\n" + resume[end_pos:]
        else:
            # No skills section found, add one
            resume += f"\n\nSKILLS\n{keyword}\n"
        return resume

    # ------------------------------------------------------------------
    # Changes summary
    # ------------------------------------------------------------------
    def _build_changes_summary(self, iteration_log: list, original: str, final: str) -> str:
        lines = []
        for entry in iteration_log:
            lines.append(f"Iteration {entry['iteration']}: Score {entry['score']}/100 ({entry['remaining_weaknesses']} weaknesses)")
        last = iteration_log[-1]
        if last['score'] >= self.target_score:
            lines.append(f"Target reached: {last['score']}/100")
        else:
            lines.append(f"Final score: {last['score']}/100 (target: {self.target_score}/100)")

        orig_lines = original.strip().split('\n')
        final_lines = final.strip().split('\n')
        lines.append(f"\nChange Stats:")
        lines.append(f"  Original: {len(orig_lines)} lines, {len(original)} chars")
        lines.append(f"  Shortlist: {len(final_lines)} lines, {len(final)} chars")

        if len(original) > 0:
            change_pct = int(abs(len(final) - len(original)) / max(len(original), 1) * 100)
            lines.append(f"  Content change: ~{change_pct}% from original")

        return "\n".join(lines)
