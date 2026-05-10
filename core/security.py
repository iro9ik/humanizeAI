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


def validate_input(text: str) -> tuple[bool, str, str, bool]:
    """
    Validates raw user input.

    Returns:
        (is_valid, status, message, injection_detected)
    """
    if not text or not text.strip():
        return False, "INVALID_INPUT", "Input text is empty.", False

    if len(text) > settings.MAX_INPUT_LENGTH:
        return (
            False,
            "INVALID_INPUT",
            f"Input exceeds maximum length of {settings.MAX_INPUT_LENGTH} characters.",
            False,
        )

    # Basic check for non-printable / binary data (allow common whitespace)
    if _contains_binary_content(text):
        return (
            False,
            "INVALID_INPUT",
            "Input contains non-text or binary content.",
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
