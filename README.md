# Noetica

Noetica is a layout-preserving PDF translator. The frontend is a Vite React app with a shadcn-style Tailwind CDN UI. The backend is FastAPI with Redis/Celery jobs, PyMuPDF PDF rewriting, and Groq translation.

## Stack

- Frontend: React, Vite, Tailwind CDN, lucide-react icons
- Backend: FastAPI, WebSockets, Redis, Celery
- PDF engine: PyMuPDF
- Translation: Groq chat completions

## Docker-Only Setup

Create `backend/.env`:

```bash
cp backend/.env.example backend/.env
```

Set `GROQ_API_KEY` in `backend/.env`.

Run the full app:

```bash
make up
```

Then open `http://localhost:5173`.

The Docker stack runs:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8010`
- Redis: internal Compose network only
- Worker: Celery PDF translation worker

Useful commands:

```bash
make build
make logs
make ps
make down
```

Override host ports when needed:

```bash
FRONTEND_HOST_PORT=5175 API_HOST_PORT=8011 make up
```

The backend uses Pipenv inside Docker. You do not need to create a local Python virtualenv or run local npm commands.

## How Translation Works

1. The frontend uploads a PDF and target language.
2. FastAPI saves the file, creates a Redis-backed job, and queues Celery work.
3. The worker opens the PDF with PyMuPDF and extracts text line bounding boxes.
4. Each detected line is sent to Groq for translation.
5. Original text rectangles are redacted while images and drawings remain.
6. Translated text is inserted back into the same rectangles with font auto-sizing.
7. WebSocket updates stream progress back to the frontend.
