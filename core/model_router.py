import re
from .config import settings

# Simple heuristic patterns for short, administrative queries
_SIMPLE_PATTERNS = re.compile(r"\b(deadline|syllabus|due date|grade|schedule)\b", re.IGNORECASE)

def select_model(prompt: str) -> str:
    """Select the appropriate Gemini model based on prompt complexity.

    - If the prompt is short (< 15 words) and matches simple administrative patterns,
      route to the lightweight ``gemini-1.5-flash`` model.
    - Otherwise, use the higher‑capacity ``gemini-1.5-pro`` model.
    """
    word_count = len(prompt.strip().split())
    if word_count < 15 and _SIMPLE_PATTERNS.search(prompt):
        return "gemini-1.5-flash"
    return "gemini-1.5-pro"

def get_model_name() -> str:
    """Return the model name selected by ``select_model`` using the default AI_MODEL
    setting from ``config.Settings`` as a fallback when no prompt is provided.
    """
    return settings.AI_MODEL
