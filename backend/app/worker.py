from pathlib import Path

from celery import Celery

from .jobs import set_job
from .pdf_translator import translate_pdf
from .settings import settings

celery_app = Celery("noetica", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task(name="translate_pdf_task")
def translate_pdf_task(
    job_id: str,
    input_path: str,
    source_language: str,
    target_language: str,
) -> None:
    output_path = settings.results_dir / f"{job_id}.pdf"

    def progress(value: float, message: str) -> None:
        set_job(job_id, status="processing", progress=round(value, 1), message=message)

    try:
        set_job(job_id, status="processing", progress=1, message="Starting translation.")
        translate_pdf(Path(input_path), output_path, source_language, target_language, progress)
        set_job(
            job_id,
            status="complete",
            progress=100,
            message="Translation complete.",
            download_url=f"/api/jobs/{job_id}/download",
        )
    except Exception as exc:
        set_job(job_id, status="failed", progress=0, message=str(exc))
        raise
