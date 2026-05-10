"""Starts the FastAPI server and an ngrok tunnel for remote testing."""
import os
import uvicorn
from pyngrok import ngrok, conf
from core.config import settings

if __name__ == "__main__":
    token = os.getenv("PYNGROK_AUTH_TOKEN")
    if token:
        conf.get_default().auth_token = token
    public_url = ngrok.connect(settings.APP_PORT, "http")
    print(f"\n{'='*60}")
    print(f"  LOCAL:    http://localhost:{settings.APP_PORT}")
    print(f"  PUBLIC:   {public_url}")
    print(f"{'='*60}\n")
    print("  Open the PUBLIC URL on your phone browser to test.")
    print(f"  Press Ctrl+C to stop.\n")
    uvicorn.run(
        "app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
    )
