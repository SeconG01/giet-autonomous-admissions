# GIET Autonomous Admissions Agent

A simplified, functional FastAPI + React/Vite demo for the GIET University autonomous admissions challenge.

## Gemini API: one-line setup

Open:

`backend/app/config.py`

Replace:

```python
GEMINI_API_KEY = "PASTE_YOUR_GEMINI_API_KEY_HERE"
```

with your real Gemini API key. The backend is where the key belongs. Do **not** paste it into `frontend/src/main.jsx`.

The current model is:

`gemini-3.1-pro-preview`

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Run frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

## What is connected

- FastAPI backend
- Gemini AI Copilot with automatic local-rule fallback
- GIET knowledge JSON
- Student/lead records
- Lead creation
- Multi-turn student conversation state
- Document verification
- Document upload
- Eligibility workflow
- Analytics
- Responsive navigation
- Dark/light theme

## If Gemini is not configured

The Copilot still works using the built-in GIET admission rules. The Settings page shows whether Gemini is connected.

## Security

`backend/app/config.py` is ignored by Git in this project. Keep it that way when using a real key. Google recommends protecting API keys and restricting them appropriately. Never commit a real API key to a public repository.
