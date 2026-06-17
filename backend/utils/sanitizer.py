import re

PII_PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone": r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    "linkedin": r'(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+',
    "github": r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+',
    "twitter": r'(?:https?://)?(?:www\.)?x\.com/[A-Za-z0-9_-]+',
}

def sanitize(text: str) -> str:
    result = text
    for name, pattern in PII_PATTERNS.items():
        result = re.sub(pattern, f"[{name}_redacted]", result)
    return result
