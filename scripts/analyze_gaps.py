import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.gemini_client import GeminiClient
from backend.services.gap_analyzer import build_analyze_prompt

SYSTEM_INSTRUCTION = """You are a senior technical recruiter at a top tech company.
You review thousands of resumes against job descriptions.
Your analysis is precise, honest, and actionable."""

def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_gaps.py <resume-text-file> <jd-text-file>")
        sys.exit(1)

    resume_path = sys.argv[1]
    jd_path = sys.argv[2]

    with open(resume_path, "r") as f:
        resume = f.read()
    with open(jd_path, "r") as f:
        jd = f.read()

    client = GeminiClient()
    prompt = build_analyze_prompt(resume, jd)
    raw = client.generate(prompt, system_instruction=SYSTEM_INSTRUCTION)

    try:
        result = json.loads(raw)
        print(json.dumps(result, indent=2))
    except json.JSONDecodeError:
        print("Gemini returned invalid JSON:")
        print(raw)

if __name__ == "__main__":
    main()
