import re
from core.config import settings

# Known prompt-injection and jailbreak keywords/phrases.
# We do not strip them; we detect them so logs can flag the attempt,
# and we rely on structural isolation (system vs user roles) to neutralize them.
_INJECTION_PATTERNS = [
    r"ignore\s+(?:previous|all|prior|the)\s+(?:instructions?|prompts?|commands?|rules?)",
    r"act\s+as\s+(?:if\s+you\s+are|like)",
    r"reveal\s+(?:your|the|system)\s+(?:prompt|instructions?|rules?)",
    r"developer\s+mode",
    r"jailbreak",
    r"\bDAN\b",
    r"roleplay",
    r"pretend\s+(?:you\s+are|to\s+be)",
    r"simulate",
    r"you\s+are\s+now\s+(?:in|free|unrestricted)",
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"anti\-?jailbreak",
]

_INJECTION_REGEX = re.compile(
    "|".join(f"(?:{p})" for p in _INJECTION_PATTERNS),
    re.IGNORECASE,
)


_COMMON_ENGLISH_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
    "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
    "even", "new", "want", "because", "any", "these", "give", "day", "most", "us"
}


def validate_input(text: str) -> tuple[bool, str, str, bool]:
    """
    Validates raw user input.

    Returns:
        (is_valid, status, message, injection_detected)
    """
    if not text or not text.strip():
        return False, "INVALID_INPUT", "INVALID_INPUT: Please provide text to transform.", False

    if len(text) > settings.MAX_INPUT_LENGTH:
        return (
            False,
            "INVALID_INPUT",
            f"INVALID_INPUT: Input exceeds maximum length of {settings.MAX_INPUT_LENGTH} characters.",
            False,
        )

    # Word count check
    words = [w for w in text.split() if w.strip()]
    if len(words) < 20:
        return (
            False,
            "INVALID_INPUT",
            "INVALID_INPUT: Text too short, minimum 20 words required.",
            False,
        )

    # Basic check for non-printable / binary data (allow common whitespace)
    if _contains_binary_content(text):
        return (
            False,
            "INVALID_INPUT",
            "INVALID_INPUT: Input contains non-text or binary content.",
            False,
        )

    # Latin character check for non-English languages (Russian, Chinese, Arabic, etc.)
    latin_chars = len(re.findall(r"[a-zA-Z]", text))
    total_chars = len(re.sub(r"\s", "", text))
    if total_chars > 0:
        latin_ratio = latin_chars / total_chars
        if latin_ratio < 0.7:
            return (
                False,
                "INVALID_INPUT",
                "INVALID_INPUT: Only English text is supported.",
                False,
            )

    # Clean words to check English words ratio (against Spanish, French, Italian, Gibberish, etc.)
    cleaned_words = [re.sub(r"[^\w']", "", w).lower() for w in words]
    cleaned_words = [w for w in cleaned_words if w]
    common_count = sum(1 for w in cleaned_words if w in _COMMON_ENGLISH_WORDS)
    common_ratio = common_count / max(1, len(cleaned_words))

    if common_ratio < 0.18:
        unique_words = len(set(cleaned_words))
        if unique_words < 5:
            return (
                False,
                "INVALID_INPUT",
                "INVALID_INPUT: Text must contain valid words.",
                False,
            )

        # Detect if it's keyboard smash/gibberish vs foreign Latin language
        vowels = len(re.findall(r"[aeiouyAEIOUY]", text))
        consonants = len(re.findall(r"[bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ]", text))
        has_smash_pattern = bool(re.search(r"[asdfghjkl;']{8,}|[qweruiop]{8,}|[zxcvbnm]{8,}", text.lower()))

        if vowels == 0 or (consonants / max(1, vowels)) > 5.0 or has_smash_pattern:
            return (
                False,
                "INVALID_INPUT",
                "INVALID_INPUT: Text must contain valid words.",
                False,
            )
        else:
            return (
                False,
                "INVALID_INPUT",
                "INVALID_INPUT: Only English text is supported.",
                False,
            )

    injection_detected = bool(_INJECTION_REGEX.search(text))
    return True, "", "", injection_detected


def _contains_binary_content(text: str) -> bool:
    # Check for a high ratio of null bytes or control characters
    null_bytes = text.count("\x00")
    control_chars = sum(1 for ch in text if ord(ch) < 32 and ch not in "\t\n\r")
    total = len(text)
    if total == 0:
        return False
    return (null_bytes / total) > 0.01 or (control_chars / total) > 0.1
