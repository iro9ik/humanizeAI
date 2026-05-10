import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import settings
from core.models import HumanizeRequest, HumanizeResponse
from core.security import validate_input
from core.services import call_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Humanizer backend on %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield
    logger.info("Shutting down AI Humanizer backend.")


app = FastAPI(
    title="AI Humanizer Engine",
    description="Secure backend text transformation engine. Not a chatbot.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("Validation error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={
            "status": "INVALID_INPUT",
            "message": str(exc),
            "output": "",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Avoid double-wrapping if the detail already follows our schema
    detail = exc.detail
    if isinstance(detail, dict) and "status" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "INVALID_INPUT",
            "message": str(detail),
            "output": "",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "INVALID_INPUT",
            "message": "Internal server error.",
            "output": "",
        },
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Humanizer</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 1rem; background: #f5f6f8; color: #111; }
        .container { max-width: 700px; margin: 0 auto; background: #fff; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        h1 { font-size: 1.25rem; margin-bottom: 0.5rem; }
        p { color: #555; font-size: 0.95rem; margin-bottom: 1rem; }
        textarea { width: 100%; min-height: 180px; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem; resize: vertical; box-sizing: border-box; }
        button { margin-top: 0.75rem; width: 100%; padding: 0.75rem; background: #111; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
        button:disabled { background: #9ca3af; cursor: not-allowed; }
        #result { margin-top: 1rem; padding: 0.75rem; background: #f3f4f6; border-radius: 8px; white-space: pre-wrap; word-wrap: break-word; display: none; }
        .status { font-weight: 600; margin-bottom: 0.25rem; }
        .error { color: #b91c1c; }
        .success { color: #047857; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Humanizer</h1>
        <p>Paste AI-generated text below. The engine will rewrite it into natural human-like writing.</p>
        <textarea id="inputText" placeholder="Paste text here..."></textarea>
        <button id="submitBtn" onclick="humanize()">Humanize</button>
        <div id="result"></div>
    </div>
    <script>
        async function humanize() {
            const btn = document.getElementById('submitBtn');
            const result = document.getElementById('result');
            const text = document.getElementById('inputText').value;
            btn.disabled = true;
            result.style.display = 'none';
            result.className = '';
            try {
                const res = await fetch('/humanize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                const data = await res.json();
                result.style.display = 'block';
                const statusClass = data.status === 'AI_GENERATED' ? 'success' : (data.status === 'INVALID_INPUT' ? 'error' : 'success');
                result.innerHTML = `<div class="status ${statusClass}">Status: ${data.status}</div><div>${data.message}</div><hr/><div>${data.output}</div>`;
            } catch (e) {
                result.style.display = 'block';
                result.className = 'error';
                result.textContent = 'Network error. Is the server running?';
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>"""


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/humanize", response_model=HumanizeResponse)
async def humanize(request: HumanizeRequest):
    raw_text = request.text

    is_valid, status, message, injection_detected = validate_input(raw_text)

    if not is_valid:
        logger.info(
            "Invalid input rejected: status=%s length=%s injection=%s",
            status,
            len(raw_text),
            injection_detected,
        )
        return HumanizeResponse(status=status, message=message, output=raw_text)

    # Safe logging: never log full text unless injection is detected (for forensics).
    if injection_detected:
        logger.warning(
            "Prompt-injection keywords detected in request (length=%s). Input blocked from override by structural isolation.",
            len(raw_text),
        )
    else:
        logger.info(
            "Humanizing request: length=%s",
            len(raw_text),
        )

    try:
        result = await call_llm(raw_text)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during humanization")
        raise HTTPException(
            status_code=500,
            detail="Humanization engine failed. Please retry.",
        ) from exc

    return HumanizeResponse(
        status=result.get("status", "INVALID_INPUT"),
        message=result.get("message", "Unexpected Error Reponse."),
        output=result.get("output", ""),
    )
