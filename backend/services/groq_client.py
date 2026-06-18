import time
import json
import hashlib
import requests
from typing import Optional
from config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ---------------------------------------------------------------------------
# Auto-routing: Groq (primary) -> OpenRouter (fallback on rate-limit / down)
# Each task has a primary model (Groq) and a fallback model (OpenRouter).
# ---------------------------------------------------------------------------
# OpenRouter models — verified working (2026)
OPENROUTER_FAST = "anthropic/claude-3.5-haiku"
OPENROUTER_QUALITY = "anthropic/claude-sonnet-4.5"

MODEL_ROUTES = {
    "analyze":              {"groq": "llama-3.1-8b-instant",     "openrouter": OPENROUTER_FAST},
    "rewrite":              {"groq": "llama-3.3-70b-versatile",  "openrouter": OPENROUTER_QUALITY},
    "full_rewrite":         {"groq": "llama-3.3-70b-versatile",  "openrouter": OPENROUTER_QUALITY},
    "simulate":             {"groq": "llama-3.3-70b-versatile",  "openrouter": OPENROUTER_QUALITY},
    "cover_letter":         {"groq": "llama-3.3-70b-versatile",  "openrouter": OPENROUTER_QUALITY},
    "keywords":             {"groq": "llama-3.1-8b-instant",     "openrouter": OPENROUTER_FAST},
    "resume_scorer":        {"groq": "llama-3.1-8b-instant",    "openrouter": OPENROUTER_FAST},
    "interview_questions":  {"groq": "llama-3.3-70b-versatile",  "openrouter": OPENROUTER_QUALITY},
    "ats_breakdown":        {"groq": "llama-3.1-8b-instant",     "openrouter": OPENROUTER_FAST},
    "shortlist":            {"groq": "llama-3.1-8b-instant",     "openrouter": OPENROUTER_FAST},
    "templates":            {"groq": "llama-3.1-8b-instant",     "openrouter": OPENROUTER_FAST},
    "recommend":            {"groq": "llama-3.1-8b-instant",    "openrouter": OPENROUTER_FAST},
}

# Per-task token limits (overrides default max_tokens)
TASK_MAX_TOKENS = {
    "analyze": settings.max_tokens_analyze,
    "rewrite": settings.max_tokens_rewrite,
    "full_rewrite": settings.max_tokens_full_rewrite,
    "simulate": settings.max_tokens_simulate,
    "cover_letter": settings.max_tokens_cover_letter,
    "keywords": settings.max_tokens_keywords,
    "resume_scorer": settings.max_tokens_score,
    "interview_questions": settings.max_tokens_interview,
    "ats_breakdown": settings.max_tokens_ats,
    "shortlist": settings.max_tokens_shortlist,
    "templates": settings.max_tokens_templates,
    "recommend": settings.max_tokens_recommend,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ``` or ``` ... ```) from text."""
    import re
    # Remove ```json ... ``` or ``` ... ``` blocks
    text = re.sub(r'^```(?:json)?\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    # Remove single backtick fences
    text = re.sub(r'^```(?:json)?', '', text)
    text = re.sub(r'```$', '', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Simple in-memory response cache (keyed by prompt+model hash)
# ---------------------------------------------------------------------------
_response_cache: dict[str, tuple[float, str]] = {}  # key -> (expiry_ts, text)


def _cache_key(prompt: str, system: Optional[str], model: str) -> str:
    raw = f"{prompt}||{system or ''}||{model}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# GroqClient with automatic OpenRouter fallback
# ---------------------------------------------------------------------------
class GroqClient:
    """AI client that tries Groq first, falls back to OpenRouter on failure.

    Both providers use the same OpenAI-compatible chat completions API, so
    the request body format is identical.
    """

    def __init__(self, task_type: str = "analyze"):
        if task_type not in MODEL_ROUTES:
            raise ValueError(f"Unknown task type: {task_type}. Valid: {list(MODEL_ROUTES.keys())}")
        self.task_type = task_type
        self.max_tokens = TASK_MAX_TOKENS.get(task_type, settings.max_tokens_full_rewrite)
        self._last_request_time = 0.0
        self._min_interval = 1.5  # slightly more aggressive than before

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate(self, prompt: str, system_instruction: Optional[str] = None, max_retries: int = 3) -> str:
        # 1. Check cache
        if settings.cache_enabled:
            cached = self._check_cache(prompt, system_instruction)
            if cached is not None:
                return cached

        # 2. Try Groq -> fallback to OpenRouter
        text = self._try_provider("groq", prompt, system_instruction, max_retries)
        if text is None:
            text = self._try_provider("openrouter", prompt, system_instruction, max_retries)

        if text is None:
            raise Exception(f"[{self.task_type}] Both Groq and OpenRouter failed after retries")

        # 3. Cache result
        if settings.cache_enabled:
            self._set_cache(prompt, system_instruction, text)

        return text

    # ------------------------------------------------------------------
    # Provider-specific calls
    # ------------------------------------------------------------------
    def _try_provider(self, provider: str, prompt: str, system: Optional[str], max_retries: int) -> Optional[str]:
        if provider == "groq":
            api_key = settings.groq_api_key
            url = GROQ_API_URL
        else:
            api_key = settings.openrouter_api_key
            url = OPENROUTER_API_URL

        if not api_key:
            return None

        model = MODEL_ROUTES[self.task_type][provider]

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": model,
            "messages": messages,
            "temperature": settings.temperature,
            "max_tokens": self.max_tokens,
        }

        # Only request JSON mode from providers that support it
        # Groq supports response_format; OpenRouter doesn't for all models
        if provider == "groq":
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ResuBoost/1.0",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://satyajeet-04.github.io/resuboost"
            headers["X-Title"] = "ResuBoost"

        session = requests.Session()
        session.headers.update(headers)

        for attempt in range(max_retries):
            try:
                self._rate_limit_wait()
                self._last_request_time = time.time()

                resp = session.post(url, json=body, timeout=60)

                if resp.status_code == 200:
                    result = resp.json()
                    choices = result.get("choices", [])
                    if not choices:
                        raise ValueError("No choices in response")
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if not text:
                        raise ValueError("Empty text in response")
                    # Strip markdown code fences that some providers wrap JSON in
                    text = _strip_markdown_fences(text)
                    return text

                error_body = resp.text
                error_code = resp.status_code

                # Transient errors -> short retry, then fallback
                if error_code in (429, 500, 502, 503):
                    if attempt < max_retries - 1:
                        wait = self._extract_retry_seconds(error_body)
                        # If retry-after is too long (>= 15s), skip retry -> fallback now
                        if wait >= 15:
                            return None
                        time.sleep(min(wait, 8))
                        continue
                    return None  # fallback to next provider

                # Auth / bad-request -> fail fast, fallback to next provider
                if error_code in (401, 403):
                    return None
                if error_code == 400:
                    body.pop("response_format", None)
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return None  # OpenRouter may not support JSON mode; try other provider

                return None  # any other error -> try next provider

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(4)
                    continue
                return None  # fallback to next provider

            except requests.exceptions.ConnectionError as e:
                return None  # network flakiness -> try other provider

        return None  # exhausted retries

    # ------------------------------------------------------------------
    # Rate-limit helper
    # ------------------------------------------------------------------
    def _rate_limit_wait(self):
        since_last = time.time() - self._last_request_time
        if since_last < self._min_interval:
            time.sleep(self._min_interval - since_last)

    @staticmethod
    def _extract_retry_seconds(msg: str) -> int:
        import re
        for pattern in [r"retry\s+after\s*(\d+)", r"try\s+again\s+in\s*(\d+)"]:
            match = re.search(pattern, msg.lower())
            if match:
                return int(match.group(1)) + 1
        return 0

    # ------------------------------------------------------------------
    # Response cache
    # ------------------------------------------------------------------
    def _check_cache(self, prompt: str, system: Optional[str]) -> Optional[str]:
        key = _cache_key(prompt, system, self.task_type)
        entry = _response_cache.get(key)
        if entry is None:
            return None
        expiry, text = entry
        if time.time() > expiry:
            del _response_cache[key]
            return None
        return text

    def _set_cache(self, prompt: str, system: Optional[str], text: str):
        key = _cache_key(prompt, system, self.task_type)
        _response_cache[key] = (time.time() + settings.cache_ttl_seconds, text)

    # ------------------------------------------------------------------
    # Cache control (for testing / admin)
    # ------------------------------------------------------------------
    @staticmethod
    def clear_cache():
        _response_cache.clear()
