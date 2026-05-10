# AI Humanizer Engine

A secure, backend-only text transformation engine built with **FastAPI** and the **DeepSeek API**.

## What it does

Receives AI-generated text, validates it, protects against prompt injection, and returns a rewritten human-like version.

This is **not** a chatbot. It is a strict text transformation engine.

## Project Structure

```
.
├── app.py              # Uvicorn entry point
├── core/
│   ├── __init__.py
│   ├── config.py       # Settings & .env loader
│   ├── main.py         # FastAPI app, routes, middleware
│   ├── models.py       # Pydantic request/response models
│   ├── prompts.py      # Fixed system prompt (edit this when ready)
│   ├── security.py     # Input validation & injection detection
│   └── services.py     # DeepSeek API client
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. **Create a virtual environment**

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in your **DeepSeek API key**:

   ```powershell
   cp .env.example .env
   ```

   Edit `.env`:

   ```env
   DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   DEEPSEEK_BASE_URL=https://api.deepseek.com
   DEEPSEEK_MODEL=deepseek-chat
   MAX_INPUT_LENGTH=5000
   REQUEST_TIMEOUT=30
   ```

4. **Customize the system prompt (optional)**

   Open `core/prompts.py` and replace the placeholder `SYSTEM_PROMPT` with your exact system prompt when ready.

## Run Locally

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000
```

- API docs (Swagger UI): `http://localhost:8000/docs`
- Test page: `http://localhost:8000/`
- Health check: `http://localhost:8000/health`

## Remote Testing with Ngrok

1. **Download and install Ngrok** from [ngrok.com](https://ngrok.com/).

2. **Authenticate** (one-time):

   ```powershell
   ngrok config add-authtoken YOUR_NGROK_TOKEN
   ```

3. **Start the backend**:

   ```powershell
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

4. **In a new terminal**, expose it:

   ```powershell
   ngrok http 8000
   ```

5. **Copy the public HTTPS URL** from the Ngrok terminal output and open it on your phone browser or API tester app.

   - The root URL `/` shows a simple paste-and-submit page.
   - The API endpoint is `POST /humanize`.

## API Endpoint

### `POST /humanize`

**Request body:**

```json
{
  "text": "Paste AI-generated text here"
}
```

**Response:**

```json
{
  "status": "AI_GENERATED",
  "message": "Text successfully humanized.",
  "output": "Rewritten natural human-like text..."
}
```

Possible `status` values:
- `AI_GENERATED` — text was rewritten.
- `HUMAN_LIKE` — input already looked human-like; original returned.
- `INVALID_INPUT` — empty, too long, or blocked content.

## Security Features

- **Structural isolation**: user input is sent only in the `user` message role; the system prompt is fixed and never interpolated with user data.
- **Prompt-injection detection**: known jailbreak keywords are flagged in logs and neutralized by wrapper instructions.
- **Length limits**: configurable via `MAX_INPUT_LENGTH`.
- **Timeout protection**: requests to DeepSeek abort after `REQUEST_TIMEOUT` seconds.
- **Safe logging**: full user text is never logged; only length and metadata are recorded.

## Next Steps

Replace the placeholder system prompt in `core/prompts.py` with your exact prompt, then test end-to-end.
