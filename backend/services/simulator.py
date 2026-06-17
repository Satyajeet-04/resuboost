from services.groq_client import GroqClient
import json

def build_simulate_prompt(resume: str, role: str) -> str:
    return f"""You are a recruiter at a company hiring for: {role}

Generate 8 realistic Boolean search strings that recruiters would use in their ATS or LinkedIn Recruiter to find candidates for this role.

For each query, evaluate whether this specific RESUME would appear.

RESUME:
{resume}

Return JSON:
{{
  "queries": [
    {{
      "query": "boolean search string",
      "match": true or false,
      "why": "Matches because... | Does NOT match because..."
    }}
  ],
  "match_rate": <integer 0-100>
}}

Rules:
- Vary specificity (some broad, some narrow).
- 4 should match, 4 should NOT match.
- For non-matches, explain exactly what's missing."""

class Simulator:
    def __init__(self):
        self.client = GroqClient(task_type="simulate")

    def simulate(self, resume: str, role: str) -> dict:
        prompt = build_simulate_prompt(resume, role)
        raw = self.client.generate(prompt)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "queries" not in result or "match_rate" not in result:
            raise ValueError("Gemini response missing 'queries' or 'match_rate' fields")
        return result
