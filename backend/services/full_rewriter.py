from services.groq_client import GroqClient
import json

def build_full_rewrite_prompt(resume: str, gaps: list[str], jd: str) -> str:
    gap_list = ", ".join(gaps)
    return f"""You are an expert resume writer. Rewrite the COMPLETE resume below to address ALL these missing skills: {gap_list}

JOB DESCRIPTION (target role):
{jd}

CURRENT RESUME:
{resume}

Return JSON. IMPORTANT: "full_resume" MUST be a single flat string of plain text, NOT a nested JSON object. It should be formatted as plain text resume with section headers like:

SUMMARY
...
EXPERIENCE
...
EDUCATION
...
SKILLS
...

{{
  "full_resume": "PLAIN TEXT RESUME HERE — do NOT use JSON objects inside this field",
  "changes_summary": "Brief bullet points explaining what was changed and why"
}}

RULES (CRITICAL):
- "full_resume" MUST be a plain text string, NOT a JSON object or array
- Do NOT fabricate experience. Only add skills in ways that are truthful based on the resume.
- For skills that truly don't exist, add them in a Skills section as "Familiar with: X" or suggest learning them.
- Preserve the original resume's sections and overall structure.
- Use action verbs and STAR format for experience bullets.
- Keep the rewrite natural and human-readable — not keyword-stuffed."""

class FullRewriter:
    def __init__(self):
        self.client = GroqClient(task_type="full_rewrite")

    def _flatten_to_text(self, obj) -> str:
        """Convert any nested JSON object back to plain text resume format."""
        if isinstance(obj, str):
            return obj
        lines = []
        if isinstance(obj, dict):
            for key, val in obj.items():
                key_str = key.replace("_", " ").upper()
                lines.append(f"\n{key_str}")
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                k_str = k.replace("_", " ").title()
                                if isinstance(v, list):
                                    for li in v:
                                        lines.append(f"  • {li}")
                                elif isinstance(v, str):
                                    lines.append(f"  • {v}")
                        elif isinstance(item, str):
                            lines.append(f"  • {item}")
                elif isinstance(val, str):
                    lines.append(f"  {val}")
                elif isinstance(val, dict):
                    lines.append(self._flatten_to_text(val))
        elif isinstance(obj, list):
            for item in obj:
                text = self._flatten_to_text(item)
                if text.strip():
                    lines.append(f"  • {text.strip()}")
        return "\n".join(lines)

    def full_rewrite(self, resume: str, gaps: list[str], jd: str) -> dict:
        prompt = build_full_rewrite_prompt(resume, gaps, jd)
        raw = self.client.generate(prompt)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        
        full_resume = result.get("full_resume", "")
        # If full_resume is a nested JSON object, flatten it to plain text
        if not isinstance(full_resume, str):
            full_resume = self._flatten_to_text(full_resume)
        
        changes = result.get("changes_summary", "")
        if not isinstance(changes, str):
            changes = self._flatten_to_text(changes)
        
        if not full_resume or len(full_resume.strip()) < 50:
            # Fallback: use the raw text
            fallback_resume = raw.strip().strip('"')
            if len(fallback_resume) > 200:
                full_resume = fallback_resume
                changes = changes or "Full resume rewritten to address missing skills."
            else:
                raise ValueError("Groq response missing 'full_resume' field")
        
        return {"full_resume": full_resume, "changes_summary": changes}
