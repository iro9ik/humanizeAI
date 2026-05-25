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
            "ai_evaluation": "INVALID_INPUT",
            "execution_mode": "UNKNOWN",
            "message": str(exc),
            "output": "",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "ai_evaluation" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ai_evaluation": "INVALID_INPUT",
            "execution_mode": "UNKNOWN",
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
            "ai_evaluation": "INVALID_INPUT",
            "execution_mode": "UNKNOWN",
            "message": "Internal server error.",
            "output": "",
        },
    )






@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/humanize", response_model=HumanizeResponse)
async def humanize(request: HumanizeRequest):
    raw_text = request.text
    mode = request.mode

    is_valid, status, message, injection_detected = validate_input(raw_text)

    if not is_valid:
        logger.info(
            "Invalid input rejected: status=%s length=%s injection=%s",
            status,
            len(raw_text),
            injection_detected,
        )
        return HumanizeResponse(
            ai_evaluation="INVALID_INPUT",
            execution_mode=mode,
            message=message,
            output=raw_text
        )

    # Safe logging: never log full text unless injection is detected (for forensics).
    if injection_detected:
        logger.warning(
            "Prompt-injection keywords detected in request (length=%s). Input blocked from override by structural isolation.",
            len(raw_text),
        )
    else:
        logger.info(
            "Transforming request (mode=%s): length=%s",
            mode,
            len(raw_text),
        )

    try:
        result = await call_llm(raw_text, mode)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during text transformation")
        raise HTTPException(
            status_code=500,
            detail={
                "ai_evaluation": "INVALID_INPUT",
                "execution_mode": mode,
                "message": "Transformation engine failed. Please retry.",
                "output": "",
            },
        ) from exc

    return HumanizeResponse(
        ai_evaluation=result.get("ai_evaluation", "INVALID_INPUT"),
        execution_mode=result.get("execution_mode", mode),
        message=result.get("message", "Unexpected Error Response."),
        output=result.get("output", ""),
    )

from fastapi.staticfiles import StaticFiles
import pathlib

# Mount the compiled React frontend static files
# In a real production deployment, Nginx or similar is preferred, but for this app it serves it directly.
# Using 'app-ui/dist' which is relative to the project root where start.bat runs, but let's resolve it carefully.
root_dir = pathlib.Path(__file__).parent.parent
frontend_dist = root_dir / "app-ui" / "dist"

# Since we want the root ("/") to serve index.html, we can use a custom route or StaticFiles with html=True
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    logger.warning(f"Frontend dist not found at {frontend_dist}. Please run 'npm run build' in app-ui/")
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return "<h1>Frontend build missing. Please build the React app first.</h1>"

