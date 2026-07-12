import asyncio
import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .jobs import create_job, get_job, job_channel, redis_client
from .settings import settings
from .worker import translate_pdf_task

app = FastAPI(title="Noetica API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def ensure_storage() -> None:
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.results_dir.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs")
async def create_translation_job(
    file: UploadFile = File(...),
    source_language: str = Form("auto"),
    target_language: str = Form(...),
) -> dict:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    job_id = uuid.uuid4().hex
    safe_name = Path(file.filename or "document.pdf").name
    input_path = settings.uploads_dir / f"{job_id}-{safe_name}"

    with input_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    state = create_job(job_id, safe_name, source_language, target_language)
    translate_pdf_task.delay(job_id, str(input_path), source_language, target_language)
    return state


@app.get("/api/jobs/{job_id}")
def read_job(job_id: str) -> dict:
    return get_job(job_id)


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    state = get_job(job_id)
    if state.get("status") != "complete":
        raise HTTPException(status_code=404, detail="Translated PDF is not ready.")

    path = settings.results_dir / f"{job_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Translated PDF was not found.")

    return FileResponse(path, media_type="application/pdf", filename=f"translated-{state.get('filename', 'document.pdf')}")


@app.websocket("/ws/jobs/{job_id}")
async def job_events(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    await websocket.send_json(get_job(job_id))
    pubsub = redis_client.pubsub()
    pubsub.subscribe(job_channel(job_id))

    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and message.get("data"):
                payload = json.loads(message["data"])
                await websocket.send_json(payload)
                if payload.get("status") in {"complete", "failed"}:
                    break
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.close()
