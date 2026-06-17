import time
import json
import requests
from config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Auto-routing: different models per task complexity
MODEL_ROUTES = {
    "analyze": "llama-3.1-8b-instant",       # simple comparison -> fast & cheap
    "rewrite": "llama-3.3-70b-versatile",     # STAR rewrite -> quality
    "full_rewrite": "llama-3.3-70b-versatile", # full resume rewrite -> best model
    "simulate": "llama-3.3-70b-versatile",    # Boolean query generation -> quality
}

class GroqClient:
    def __init__(self, task_type: str = "analyze"):
        if task_type not in MODEL_ROUTES:
            raise ValueError(f"Unknown task type: {task_type}. Valid: {list(MODEL_ROUTES.keys())}")
        self.api_key = settings.groq_api_key
        self.model = MODEL_ROUTES[task_type]
        self.task_type = task_type
        self.timeout = 45
        self._last_request_time = 0.0
        self._min_interval = 2.0  # 30 req/min on Groq free tier -> 2s between requests

    def generate(self, prompt: str, system_instruction: str = None, max_retries=3) -> str:
        # Client-side rate limiting
        since_last = time.time() - self._last_request_time
        if since_last < self._min_interval:
            time.sleep(self._min_interval - since_last)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ResuBoost/1.0",
        }

        session = requests.Session()
        session.headers.update(headers)

        for attempt in range(max_retries):
            try:
                self._last_request_time = time.time()
                resp = session.post(
                    GROQ_API_URL,
                    json=body,
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    result = resp.json()
                    choices = result.get("choices", [])
                    if not choices:
                        raise ValueError("No choices in Groq response")
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if not text:
                        raise ValueError("Empty text in Groq response")
                    return text

                # Handle errors
                error_body = resp.text
                error_code = resp.status_code

                # Retry only 429 (rate limit) and 5xx (server overload)
                if error_code in (429, 500, 502, 503) and attempt < max_retries - 1:
                    retry_sec = self._extract_retry_seconds(error_body)
                    sleep_time = min(max(retry_sec, 3) if retry_sec else 4, 30)
                    time.sleep(sleep_time)
                    continue

                raise Exception(f"Groq API error {error_code}: {error_body[:500]}")

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(4)
                    continue
                raise Exception("Groq API timeout after retries")

            except requests.exceptions.ConnectionError as e:
                raise Exception(f"Groq connection error: {str(e)[:200]}")

    def _extract_retry_seconds(self, msg: str) -> int:
        import re
        match = re.search(r"retry\s+after\s*(\d+)", msg.lower())
        if match:
            return int(match.group(1)) + 1
        match = re.search(r"try\s+again\s+in\s*(\d+)", msg.lower())
        if match:
            return int(match.group(1)) + 1
        return 0
