import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    max_tokens: int = 2048
    temperature: float = 0.2
    strip_pii: bool = True
    max_input_length: int = 50000

    class Config:
        env_file = ".env"

settings = Settings()
