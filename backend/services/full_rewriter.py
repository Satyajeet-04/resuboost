"""Token-optimized full resume rewriter."""
from services.groq_client import GroqClient
import json

PROMPT_TEMPLATE = """Rewrite the COMPLETE resume to address missing skills: {gaps}

JD (target role): {jd}

CURRENT RESUME: {resume}

Return JSON. "full_resume" MUST be plain text (no nested JSON), formatted with section headers:

SUMMARY\n...\nEXPERIENCE\n...\nEDUCATION\n...\nSKILLS\n...

{{
  "full_resume": "plain text resume",
  "changes_summary": "what changed and why"
}}
Rules: No fabricated experience. Add unfamiliar skills as 'Familiar with: X'. Use action verbs, STAR format. Natural, not keyword-stuffed."""

class FullRewriter:
    def __init__(self):
        self.client = GroqClient(task_type="full_rewrite")

    def _flatten_to_text(self, obj) -> str:
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
        gap_str = ", ".join(gaps)
        raw = self.client.generate(PROMPT_TEMPLATE.format(resume=resume, gaps=gap_str, jd=jd))
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")

        full_resume = result.get("full_resume", "")
        if not isinstance(full_resume, str):
            full_resume = self._flatten_to_text(full_resume)

        changes = result.get("changes_summary", "")
        if not isinstance(changes, str):
            changes = self._flatten_to_text(changes)

        if not full_resume or len(full_resume.strip()) < 50:
            fallback = raw.strip().strip('"')
            if len(fallback) > 200:
                full_resume = fallback
            else:
                raise ValueError("Response missing valid 'full_resume' field")

        return {"full_resume": full_resume, "changes_summary": changes or "Full resume rewritten."}
