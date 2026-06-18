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
            return [k for k in result if isinstance(k, str) and len(k) > 0]
        # Fallback: simple extraction
        tech_words = re.findall(r'\b[A-Z][A-Za-z0-9+#.]+(?:\s*[A-Z][A-Za-z0-9+#.]+)*\b', jd)
        return list(set(w for w in tech_words if len(w) > 1))[:20]

    # ------------------------------------------------------------------
    # Score resume
    # ------------------------------------------------------------------
    def _score_resume(self, resume: str, jd: str) -> dict:
        # First compute a fast keyword-based score as baseline
        kw_score, kw_weaknesses = self._keyword_based_score(resume, jd)
        
        groq = GroqClient(task_type="resume_scorer")
        prompt = f"""Score this resume against the job description (0-100).

JD:
{jd[:3000]}

Resume:
{resume[:3000]}

Base keyword coverage suggests: {kw_score}/100

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
            # Blend AI score with keyword score to be fair
            ai_score = result.get("overall_score", 0)
            blended = max(kw_score, ai_score)  # take the higher of the two
            result["overall_score"] = blended
            # Add missing keywords as weaknesses if not already there
            existing = [w.lower() for w in result.get("weaknesses", []) if w and isinstance(w, str)]
            for kw in kw_weaknesses:
                if kw.lower() not in existing:
                    result["weaknesses"] = result.get("weaknesses", []) + [f"Missing keyword: {kw}"]
            return result
        return {"overall_score": kw_score, "strengths": [], "weaknesses": kw_weaknesses[:5]}

    def _keyword_based_score(self, resume: str, jd: str) -> tuple:
        """Fast keyword-based scoring as fallback/blend baseline."""
        resume_lower = resume.lower()
        jd_lower = jd.lower()
        
        # Extract meaningful words from JD
        tech_terms = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
            'rest', 'graphql', 'api', 'microservices',
            'ci/cd', 'agile', 'scrum', 'devops',
            'machine learning', 'deep learning', 'nlp', 'pytorch', 'tensorflow',
            'kafka', 'rabbitmq', 'spark', 'airflow',
            'system design', 'distributed systems', 'scalability',
            'c++', 'golang', 'rust', 'swift', 'kotlin',
            'tableau', 'power bi', 'looker', 'snowflake',
            'excel', 'jira', 'confluence',
            'leadership', 'communication', 'team management', 'cross-functional',
            'agile', 'scrum', 'kanban', 'product management',
            'data structures', 'algorithms', 'optimization',
        ]
        
        found_in_jd = [t for t in tech_terms if t in jd_lower]
        if not found_in_jd:
            return 60, ["general keyword alignment"]
        
        matched = [t for t in found_in_jd if t in resume_lower]
        missing = [t for t in found_in_jd if t not in resume_lower]
        
        score = int((len(matched) / max(len(found_in_jd), 1)) * 100)
        # Bonus for having professional summary, skills section, quantified metrics
        if re.search(r'(?i)(professional summary|summary|profile)', resume):
            score = min(100, score + 5)
        if re.search(r'(?i)skills', resume):
            score = min(100, score + 5)
        if re.search(r'\d+%|\d+x|\$\d+', resume):
            score = min(100, score + 5)
        
        return score, missing

    # ------------------------------------------------------------------
    # Aggressive rewrite with keyword injection
    # ------------------------------------------------------------------
    def _keyword_inject_rewrite(self, resume: str, original: str, jd: str,
                                 jd_keywords: list, gaps: list, final_pass: bool) -> str:
        groq = GroqClient(task_type="shortlist")

        # Filter to only valid strings (AI sometimes returns null entries)
        valid_kws = [k for k in jd_keywords if isinstance(k, str) and len(k) > 0]
        missing_kws = [k for k in valid_kws if k.lower() not in resume.lower()]

        prompt = f"""You are an expert ATS resume optimizer. REWRITE this resume to score HIGH on ATS filters.

JOB DESCRIPTION (TARGET):
{jd[:3500]}

ORIGINAL RESUME:
{original[:3000]}

CURRENT VERSION:
{resume[:3000]}

JD KEYWORDS NOT IN RESUME (INJECT):
{', '.join(missing_kws[:15])}

GAPS TO FIX:
{', '.join(gaps)}

{'FINAL PASS - MAXIMUM EFFORT' if final_pass else 'IMPROVE THIS RESUME'}

OUTPUT FORMAT:
Name
Contact Info

PROFESSIONAL SUMMARY
[3-5 sentences mirroring JD language, incorporating key JD keywords naturally]

SKILLS
Languages: Python, Java, ...
Cloud & DevOps: AWS, Docker, ...
Frameworks: React, Node.js, ...
Databases: SQL, ...
Tools: Git, ...

EXPERIENCE
Company Name | Role | Dates
- Rewritten bullet that naturally includes JD keywords as part of actual work context
- Each bullet uses a DIFFERENT strong verb (Architected, Engineered, Optimized, Deployed, etc.)
- Every bullet is unique in wording from the original

EDUCATION
Degree | School | Year

INSTRUCTIONS:
1. Create a PROFESSIONAL SUMMARY section incorporating JD language
2. CATEGORIZE skills matching JD requirements (add missing keywords to appropriate groups)
3. Rewrite experience bullets with DIFFERENT verbs and structure from original
4. Each keyword appears ONCE naturally, not repeated in every bullet
5. DONT say "leveraging [keyword]" more than once — vary the phrasing

RULES:
- KEEP: real company names, dates, degrees, certifications, titles
- ADD: missing JD keywords naturally into skills and experience context
- NEVER add: fake degrees, fake companies, fake credentials
- NO tables, columns, markdown formatting

Return JSON:
{{{{
  "full_resume": "the COMPLETE rewritten resume with all sections",
  "changes_summary": "specific changes made"
}}}}"""
        system = "You are an ATS resume expert. Create a keyword-optimized resume with natural language and clean structure. Never repeat the same phrasing twice."

        text = groq.generate(prompt, system)
        result = _robust_json_parse(text)
        if isinstance(result, dict):
            rewritten = result.get("full_resume", resume)
            # Ensure at least SOME keywords made it
            for kw in valid_kws[:10]:
                if kw.lower() not in rewritten.lower():
                    rewritten = self._inject_keyword(rewritten, kw)
            return rewritten

        # Fallback: inject keywords minimally
        result = resume
        for kw in valid_kws[:10]:
            if kw.lower() not in result.lower():
                result = self._inject_keyword(result, kw)
        return result

    # ------------------------------------------------------------------
    # Fallback keyword injector
    # ------------------------------------------------------------------
    def _inject_keyword(self, resume: str, keyword: str) -> str:
        """Inject a missing keyword into skills + experience bullets."""
        if not isinstance(keyword, str) or len(keyword) == 0:
            return resume
        if keyword.lower() in resume.lower():
            return resume
        
        # 1. Add to Skills section
        skills_match = re.search(r'(?i)(SKILLS|TECHNICAL SKILLS|TECHNOLOGIES|EXPERTISE)\s*\n', resume)
        if skills_match:
            pos = skills_match.end()
            next_section = re.search(r'\n(?=[A-Z][A-Za-z\s]+:\s*\n|\n[A-Z][A-Za-z\s]+\n[-=]+\n)', resume[pos:])
            end_pos = pos + (next_section.start() if next_section else len(resume[pos:]))
            resume = resume[:end_pos].rstrip() + f", {keyword}\n" + resume[end_pos:]
        else:
            resume += f"\n\nSKILLS\n{keyword}\n"
        
        # 2. Also inject into at least one experience bullet
        bullet_pattern = re.compile(r'^[-*•]\s+', re.MULTILINE)
        bullets = list(bullet_pattern.finditer(resume))
        if bullets:
            # Pick a random bullet to enhance
            import random
            bullet = random.choice(bullets)
            old_bullet_text = bullet.group()
            # Find the end of this bullet (next bullet or blank line or end)
            after_start = bullet.end()
            next_bullet = bullet_pattern.search(resume[after_start:])
            if next_bullet:
                bullet_end = after_start + next_bullet.start()
            else:
                # End of line or section
                line_end = resume.find('\n', after_start)
                bullet_end = line_end if line_end > 0 else len(resume)
            
            old_line = resume[after_start:bullet_end].strip()
            if keyword.lower() not in old_line.lower():
                new_line = old_line.rstrip('.')
                import random as _rnd
                prefix = _rnd.choice([" utilizing ", " with expertise in ", ", experienced in ", ", skilled in ", ", proficient with "])
                resume = resume[:bullet_end] + f"{prefix}{keyword}" + resume[bullet_end:]
        
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
