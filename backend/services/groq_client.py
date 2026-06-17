import time
import json
import urllib.request
import urllib.error
from config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Auto-routing: different models per task complexity
MODEL_ROUTES = {
    "analyze": "llama-3.1-8b-instant",       # simple comparison → fast & cheap
    "rewrite": "llama-3.3-70b-versatile",     # STAR rewrite → quality
    "full_rewrite": "llama-3.3-70b-versatile", # full resume rewrite → best model
    "simulate": "llama-3.3-70b-versatile",    # Boolean query generation → quality
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
        self._min_interval = 2.0  # 30 req/min on Groq free tier → 2s between requests

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

        data = json.dumps(body).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    GROQ_API_URL, data=data, headers=headers,
                )
                self._last_request_time = time.time()
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())

                choices = result.get("choices", [])
                if not choices:
                    raise ValueError("No choices in Groq response")
                text = choices[0].get("message", {}).get("content", "").strip()
                if not text:
                    raise ValueError("Empty text in Groq response")
                return text

            except urllib.error.HTTPError as e:
                error_body = self._read_error_body(e)
                # Retry only 429 (rate limit) and 5xx (server overload)
                if e.code in (429, 500, 502, 503) and attempt < max_retries - 1:
                    retry_sec = self._extract_retry_seconds(error_body)
                    sleep_time = min(max(retry_sec, 3) if retry_sec else 4, 30)
                    time.sleep(sleep_time)
                    continue
                raise Exception(f"Groq API error {e.code}: {error_body[:500]}")

            except Exception as e:
                if attempt < max_retries - 1 and self._is_retryable(e):
                    time.sleep(4)
                    continue
                raise

    def _read_error_body(self, e: urllib.error.HTTPError) -> str:
        try:
            return e.read().decode(errors="replace") if e.fp else ""
        except Exception:
            return ""

    def _extract_retry_seconds(self, msg: str) -> int:
        import re
        # Groq returns retry-after in various formats
        match = re.search(r"retry\s+after\s*(\d+)", msg.lower())
        if match:
            return int(match.group(1)) + 1
        match = re.search(r"try\s+again\s+in\s*(\d+)", msg.lower())
        if match:
            return int(match.group(1)) + 1
        return 0

    def _is_retryable(self, e: Exception) -> bool:
        msg = str(e).lower()
        return any(kw in msg for kw in ["timeout", "rate", "quota", "try again", "retry"])
