# AI Humanizer

A highly optimized, premium text transformation platform featuring a robust **FastAPI backend** and a stunning, responsive **Vite + React frontend**. It allows users to convert AI-generated text into multiple stylized tones (Humanizer, Clear, Professional, Academic, Creative) with strict paragraph structure preservation and industrial-grade input validation.

---

## Key Features

* **Multi-Tone Transformations**: Support for multiple professional rewriting modes:
  * **Humanizer**: Strips machine signatures to sound organic and conversational.
  * **Clear**: Maximizes readability and gets straight to the point.
  * **Professional**: Authoritative, polished business-level tone.
  * **Academic**: Scholarly, analytically rigorous third-person style.
  * **Creative**: Expressive flair, rich rhythmic styling, and vivid imagery.
* **Strict Paragraph Preservation**: Retains exact line breaks, white spaces, and structural layout from original text.
* **Smart UI Features**:
  * **Interactive Diff Viewer**: Highlights changed/modified words so users can easily see edits.
  * **Dynamic Validation**: Live word counter, foreign-language detector, and keyboard-smash validator.
  * **One-Click Actions**: Copy output or restore original input.
* **Industrial Reliability**:
  * **Transient Retry Engine**: Automatically retries upstream API requests (502, 503, 504) up to 2 times with exponential backoff.
  * **Security Guardrails**: Neutralizes prompt-injection keywords and blocks execution context overrides.
  * **Optimized Prompt Engineering**: Token-compressed prompt architecture to minimize processing latency and cost.

---

## Project Structure

```text
.
├── app.py              # Uvicorn entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables example template
├── core/               # FastAPI Backend Module
│   ├── config.py       # Pydantic settings & .env loader
│   ├── main.py         # FastAPI routing, middleware, & StaticFiles mount
│   ├── models.py       # Request/Response schemas
│   ├── prompts.py      # Compressed multi-phase prompt system
│   ├── security.py     # Live input validation & guardrails
│   └── services.py     # LLM integration client with backoff retries
└── app-ui/             # React Frontend Module
    ├── src/            # Components, styles, assets
    ├── package.json    # Node dependencies
    ├── vite.config.ts  # Vite configuration
    └── tsconfig.json   # TypeScript settings
```

---

## Getting Started (Local Development)

### 1. Backend Setup (FastAPI)

1. **Create and activate a virtual environment**:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the root directory matching your `.env.example`:
   ```env
   DEEPSEEK_API_KEY=your_openrouter_api_key_here
   DEEPSEEK_BASE_URL=https://openrouter.ai/api/v1
   DEEPSEEK_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
   MAX_INPUT_LENGTH=5000
   REQUEST_TIMEOUT=60
   ```

---

### 2. Frontend Setup (React UI)

1. **Navigate to the frontend directory**:
   ```powershell
   cd app-ui
   ```

2. **Install dependencies**:
   ```powershell
   npm install
   ```

---

## Running the Application

### Option A: Running in Development Mode (Recommended)

Start both modules in separate terminal shells to enable Hot-Module Reloading (HMR) for both codebases.

1. **Start the Backend**:
   In the root directory, run:
   ```powershell
   uvicorn app:app --host 127.0.0.1 --port 8000 --reload
   ```
   * *API Documentation*: `http://127.0.0.1:8000/docs` (Swagger UI)
   * *Health check*: `http://127.0.0.1:8000/health`

2. **Start the Frontend**:
   In the `app-ui/` directory, run:
   ```powershell
   npm run dev
   ```
   * *Web interface*: Open `http://localhost:5173/` in your browser.

---

### Option B: Unified Production Build

You can compile the React app and serve it directly from the FastAPI backend:

1. **Build the Frontend**:
   In the `app-ui/` directory, run:
   ```powershell
   npm run build
   ```
   This generates static assets in the `app-ui/dist/` directory.

2. **Run the Backend**:
   FastAPI will automatically serve the built static UI files directly from `http://127.0.0.1:8000/`.
   ```powershell
   uvicorn app:app --host 127.0.0.1 --port 8000
   ```

---

## API Documentation

### `POST /humanize`

Processes input text and rewrites it in the designated tone mode.

#### Request Schema:
```json
{
  "text": "Artificial intelligence has fundamentally transformed the landscape of modern technology. The implementation of sophisticated machine learning methodologies has facilitated unprecedented advancements.",
  "mode": "HUMANIZER"
}
```
* *Modes*: `"HUMANIZER"`, `"CLEAR"`, `"PROFESSIONAL"`, `"ACADEMIC"`, `"CREATIVE"`

#### Response Schema:
```json
{
  "ai_evaluation": "AI_GENERATED",
  "execution_mode": "HUMANIZER",
  "message": "Your text now reads naturally, like a human wrote it.",
  "output": "AI is changing how modern technology works. Using smart algorithms has led to amazing progress."
}
```

* **ai_evaluation** values:
  * `AI_GENERATED` — Text successfully rewritten.
  * `HUMAN_LIKE` — Original text was already high-quality/natural; returned untouched.
  * `INVALID_INPUT` — Rejected due to length limits, foreign languages, or bad characters.
