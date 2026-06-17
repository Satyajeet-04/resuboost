import time
from google import genai
from config import settings

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

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
                return response.text

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
