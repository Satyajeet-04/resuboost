import time
import re
from google import genai
from config import settings

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    def _is_rate_limit(self, e: Exception) -> bool:
        """Check if exception is a rate limit (429) error."""
        msg = str(e).lower()
        return "429" in msg or "quota" in msg or "resource_exhausted" in msg or "rate_limit" in msg

    def _extract_retry_seconds(self, e: Exception) -> int:
        """Extract retry-after seconds from error message if present."""
        msg = str(e)
        match = re.search(r'retry\s+in\s*(\d+\.?\d*)', msg)
        if match:
            return int(float(match.group(1))) + 2
        return 0

    def generate(self, prompt: str, system_instruction: str = None, max_retries=3) -> str:
        for attempt in range(max_retries):
            try:
                config = {
                    "response_mime_type": "application/json",
                    "temperature": settings.temperature,
                    "max_output_tokens": settings.max_tokens,
                }
                kwargs = {
                    "model": self.model,
                    "contents": prompt,
                    "config": config,
                }
                if system_instruction:
                    kwargs["config"]["system_instruction"] = system_instruction

                response = self.client.models.generate_content(**kwargs)
                if not response or not response.text:
                    raise ValueError("Empty response from Gemini API")
                return response.text

            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                if self._is_rate_limit(e):
                    retry_sec = self._extract_retry_seconds(e)
                    if retry_sec > 0:
                        time.sleep(min(retry_sec, 60))
                    else:
                        time.sleep(10 * (attempt + 1))
                else:
                    time.sleep(2 ** attempt)
