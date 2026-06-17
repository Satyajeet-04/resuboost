import time
import re
import json
import urllib.request
import urllib.error
from config import settings

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

class GeminiClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.timeout = 45  # seconds per request

    def _is_rate_limit(self, e: Exception) -> bool:
        msg = str(e).lower()
        return "429" in msg or "quota" in msg or "resource_exhausted" in msg or "rate_limit" in msg

    def _extract_retry_seconds(self, e: Exception) -> int:
        msg = str(e)
        match = re.search(r'retry\s+in\s*(\d+\.?\d*)', msg)
        if match:
            return int(float(match.group(1))) + 2
        return 0

    def generate(self, prompt: str, system_instruction: str = None, max_retries=3) -> str:
        url = f"{GEMINI_API_URL}/{self.model}:generateContent?key={self.api_key}"

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": settings.temperature,
                "max_output_tokens": settings.max_tokens,
            }
        }
        if system_instruction:
            body["system_instruction"] = {"parts": [{"text": system_instruction}]}

        data = json.dumps(body).encode()

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())

                candidates = result.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates in Gemini response")
                parts = candidates[0].get("content", {}).get("parts", [])
                text = parts[0].get("text", "").strip() if parts else ""
                if not text:
                    raise ValueError("Empty text in Gemini response")
                return text

            except urllib.error.HTTPError as e:
                # Only retry on 429 (rate limit) - it returns fast
                if e.code == 429 and attempt < max_retries - 1:
                    error_body = e.read().decode() if e.fp else ""
                    retry_sec = self._extract_retry_seconds(Exception(error_body))
                    time.sleep(min(max(retry_sec, 5) if retry_sec else 10, 60))
                    continue
                # Non-429 errors: fail immediately, no retry
                error_body = e.read().decode() if e.fp else ""
                raise Exception(f"Gemini API error {e.code}: {error_body}")

            except Exception as e:
                # Retry only rate-limit-like errors; timeout/slow: no retry
                if attempt < max_retries - 1 and self._is_rate_limit(e):
                    retry_sec = self._extract_retry_seconds(e)
                    time.sleep(min(retry_sec or 10, 60))
                    continue
                raise  # timeout or other error — fail immediately
