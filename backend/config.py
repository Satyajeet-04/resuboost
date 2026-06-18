import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Per-endpoint token limits for efficiency
    max_tokens_analyze: int = 512
    max_tokens_rewrite: int = 1024
    max_tokens_full_rewrite: int = 2048
    max_tokens_simulate: int = 1024
    max_tokens_cover_letter: int = 1024
    max_tokens_keywords: int = 512
    max_tokens_score: int = 1024
    max_tokens_interview: int = 1536
    max_tokens_ats: int = 512
    max_tokens_shortlist: int = 2048
    max_tokens_templates: int = 1024
    max_tokens_recommend: int = 1024
    
    temperature: float = 0.2
    strip_pii: bool = True
    max_input_length: int = 50000
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    class Config:
        env_file = ".env"

settings = Settings()
