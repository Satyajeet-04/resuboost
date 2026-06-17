import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.gemini_client import GeminiClient
from backend.services.rewriter import build_rewrite_prompt

def main():
    if len(sys.argv) < 3:
        print("Usage: python rewrite.py <resume-text-file> <skill> [context]")
        sys.exit(1)

    resume_path = sys.argv[1]
    skill = sys.argv[2]
    context = sys.argv[3] if len(sys.argv) > 3 else ""

    with open(resume_path, "r") as f:
        resume = f.read()

    client = GeminiClient()
    prompt = build_rewrite_prompt(resume, skill, context)
    raw = client.generate(prompt)

    try:
        result = json.loads(raw)
        print(json.dumps(result, indent=2))
    except json.JSONDecodeError:
        print("Gemini returned invalid JSON:")
        print(raw)

if __name__ == "__main__":
    main()
