from services.gemini_client import GeminiClient
import json

def build_simulate_prompt(resume: str, role: str) -> str:
    return f"""You are a recruiter at a company hiring for: {role}

Generate 15 realistic Boolean search strings that recruiters would use in their ATS or LinkedIn Recruiter to find candidates for this role.

For each query, evaluate whether this specific RESUME would appear in the search results.

RESUME:
{resume}

Return JSON:
{{
  "queries": [
    {{
      "query": "boolean search string (e.g., \\"(react OR angular) AND (typescript OR javascript) AND aws\\")",
      "match": true or false,
      "why": "Resume matches because... | Resume does NOT match because..."
    }}
  ],
  "match_rate": <integer 0-100 = percentage of queries that match>
}}

Rules:
- Queries should be realistic recruiter searches (mix of AND/OR, skills, years, roles).
- Queries should vary in specificity (some broad, some narrow).
- 7-8 should match, 7-8 should NOT match (to show gaps).
- For non-matches, explain exactly what's missing."""

class Simulator:
    def __init__(self):
        self.client = GeminiClient()

    def simulate(self, resume: str, role: str) -> dict:
        prompt = build_simulate_prompt(resume, role)
        raw = self.client.generate(prompt)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict, got {type(result).__name__}")
        if "queries" not in result or "match_rate" not in result:
            raise ValueError("Gemini response missing 'queries' or 'match_rate' fields")
        return result
