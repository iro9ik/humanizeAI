import json
import logging
import re
import httpx
from fastapi import HTTPException

from core.config import settings
from core.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_DEEPSEEK_CHAT_ENDPOINT = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"


_REQUIRED_RESPONSE_KEYS = {"status", "message", "output"}


def _extract_json(text: str) -> dict:
    """Extract a JSON object from raw text, handling markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Fallback: first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from response")


async def call_llm(raw_text: str) -> dict:
    """
    Sends the raw text to the LLM API (OpenRouter) with a fixed system prompt.

    Returns:
        A dict with keys: status, message, output.

    Raises:
        HTTPException: on API failure, timeout, or unreadable response.
    """
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost",
        "X-Title": "AI Humanizer Engine",
    }

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                _DEEPSEEK_CHAT_ENDPOINT,
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        logger.error("LLM API timeout after %ss", settings.REQUEST_TIMEOUT)
        raise HTTPException(
            status_code=504,
            detail="Upstream timed out. Please try again later.",
        ) from exc
    except httpx.NetworkError as exc:
        logger.error("network error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Unable to reach. Please check your network.",
        ) from exc

    if response.status_code >= 500:
        logger.error(
            "server error: status=%s body=%s",
            response.status_code,
            response.text[:200],
        )
        raise HTTPException(
            status_code=502,
            detail="Please retry shortly.",
        )

    if response.status_code >= 400:
        logger.error(
            "client error: status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
        raise HTTPException(
            status_code=401 if response.status_code == 401 else 400,
            detail="Request to the server was rejected.",
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        logger.error("invalid JSON: %s", response.text[:200])
        raise HTTPException(
            status_code=502,
            detail="Invalid response",
        ) from exc

    try:
        choices = data["choices"]
        if not choices:
            raise KeyError("choices empty")
        message = choices[0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("unexpected schema: %s", data)
        raise HTTPException(
            status_code=502,
            detail="Unexpected response",
        ) from exc

    if not isinstance(content, str):
        logger.error("content is not a string: %s", type(content))
        raise HTTPException(
            status_code=502,
            detail="Please try again later",
        )

    try:
        result = _extract_json(content)
    except ValueError as exc:
        logger.error("Failed to parse JSON from response: %s", content[:500])
        raise HTTPException(
            status_code=502,
            detail="the service returned an unreadable response format.",
        ) from exc

    missing = _REQUIRED_RESPONSE_KEYS - result.keys()
    if missing:
        logger.error("JSON missing keys %s: %s", missing, result)
        raise HTTPException(
            status_code=502,
            detail="the service returned an incomplete response.",
        )

    return result
