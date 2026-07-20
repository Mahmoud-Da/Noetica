import json
import time
from typing import Any

from redis import Redis

from .settings import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def job_key(job_id: str) -> str:
    return f"noetica:job:{job_id}"


def job_channel(job_id: str) -> str:
    return f"noetica:job-events:{job_id}"


def set_job(job_id: str, **updates: Any) -> dict[str, Any]:
    current = get_job(job_id)
    current.update(updates)
    current["updated_at"] = time.time()
    redis_client.set(job_key(job_id), json.dumps(current), ex=60 * 60 * 24)
    redis_client.publish(job_channel(job_id), json.dumps(current))
    return current


def create_job(
    job_id: str,
    filename: str,
    source_language: str,
    target_language: str,
    page_from: int,
    page_to: int,
) -> dict[str, Any]:
    state = {
        "job_id": job_id,
        "filename": filename,
        "source_language": source_language,
        "target_language": target_language,
        "page_from": page_from,
        "page_to": page_to,
        "status": "queued",
        "progress": 0,
        "message": "Queued for translation.",
        "download_url": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    redis_client.set(job_key(job_id), json.dumps(state), ex=60 * 60 * 24)
    return state


def get_job(job_id: str) -> dict[str, Any]:
    raw = redis_client.get(job_key(job_id))
    if not raw:
        return {"job_id": job_id, "status": "failed", "progress": 0, "message": "Job not found."}
    return json.loads(raw)
