import asyncio
import json
import logging
import re
import httpx
from fastapi import HTTPException

from core.config import settings
from core.prompts import get_system_prompt

logger = logging.getLogger(__name__)

_DEEPSEEK_CHAT_ENDPOINT = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"


_REQUIRED_RESPONSE_KEYS = {"ai_evaluation", "execution_mode", "message", "output"}

_MAX_RETRIES = 2          # up to 3 total attempts
_RETRY_BASE_DELAY = 2.0   # seconds — doubles each retry


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


async def _send_request(headers: dict, payload: dict) -> httpx.Response:
    """Send a single HTTP request to the LLM API with retry on transient errors."""
    timeout = httpx.Timeout(settings.REQUEST_TIMEOUT, connect=10.0)
    last_exc = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    _DEEPSEEK_CHAT_ENDPOINT,
                    headers=headers,
                    json=payload,
                )

            # Retry on transient server errors (502, 503, 504, 529)
            if response.status_code in (502, 503, 504, 529):
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Transient %s from upstream (attempt %d/%d). Retrying in %.1fs…",
                    response.status_code, attempt + 1, _MAX_RETRIES + 1, delay,
                )
                last_exc = HTTPException(status_code=502, detail="Upstream server error. Retrying…")
                await asyncio.sleep(delay)
                continue

            return response

        except httpx.TimeoutException:
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Timeout (attempt %d/%d). Retrying in %.1fs…",
                attempt + 1, _MAX_RETRIES + 1, delay,
            )
            last_exc = HTTPException(status_code=504, detail="Upstream timed out. Please try again later.")
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)
                continue

        except httpx.NetworkError as exc:
            logger.error("Network error: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Unable to reach the server. Please check your network.",
            ) from exc

    # All retries exhausted
    logger.error("All %d attempts failed.", _MAX_RETRIES + 1)
    raise last_exc or HTTPException(status_code=502, detail="Please retry shortly.")


async def call_llm(raw_text: str, mode: str) -> dict:
    """
    Sends the raw text to the LLM API (OpenRouter) with retry logic.

    Returns:
        A dict with keys: ai_evaluation, execution_mode, message, output.

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
            {"role": "system", "content": get_system_prompt(mode)},
            {"role": "user", "content": raw_text},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    response = await _send_request(headers, payload)

    # Non-retryable client errors
    if response.status_code >= 400:
        logger.error(
            "Client error: status=%s body=%s",
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
        logger.error("Invalid JSON from API: %s", response.text[:200])
        raise HTTPException(status_code=502, detail="Invalid response from server.") from exc

    try:
        choices = data["choices"]
        if not choices:
            raise KeyError("choices empty")
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected API schema: %s", data)
        raise HTTPException(status_code=502, detail="Unexpected response structure.") from exc

    if not isinstance(content, str):
        logger.error("Content is not a string: %s", type(content))
        raise HTTPException(
            status_code=502,
            detail="Please try again later.",
        )

    try:
        result = _extract_json(content)
    except ValueError as exc:
        logger.error("Failed to parse JSON from LLM output: %s", content[:500])
        raise HTTPException(
            status_code=502,
            detail="The service returned an unreadable response.",
        ) from exc

    missing = _REQUIRED_RESPONSE_KEYS - result.keys()
    if missing:
        logger.error("JSON missing keys %s: %s", missing, result)
        raise HTTPException(
            status_code=502,
            detail="The service returned an incomplete response.",
        )

    # Post-processing: force HUMAN_LIKE if output is identical to input
    out_text = result.get("output", "").strip()
    orig_text = raw_text.strip()
    
    if out_text == orig_text or result.get("ai_evaluation") == "HUMAN_LIKE":
        result["output"] = raw_text
        result["ai_evaluation"] = "HUMAN_LIKE"
        
        mode_upper = mode.upper()
        if mode_upper == "HUMANIZER":
            result["message"] = "Your text already reads naturally like a human. No changes were needed."
        elif mode_upper == "CLEAR":
            result["message"] = "Your text is already clear and easy to read. No changes were needed."
        elif mode_upper == "PROFESSIONAL":
            result["message"] = "Your text already sounds very professional. No changes were needed."
        elif mode_upper == "ACADEMIC":
            result["message"] = "Your text already matches an academic style. No changes were needed."
        elif mode_upper == "CREATIVE":
            result["message"] = "Your text is already creative and expressive. No changes were needed."
        else:
            result["message"] = "Your text is already excellent. No changes were needed."

    return result
