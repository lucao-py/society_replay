import threading
from datetime import datetime
from typing import Optional

from src.config import JOBS_JSON, CLIPS_JSON
from src.storage import read_json, write_json, append_json_item
from src.ffmpeg_service import create_clip
from src.preview_service import create_preview, get_preview_path
from src.utils import generate_id

_job_lock = threading.Lock()
_worker_lock = threading.Lock()
_worker_running = False


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def list_jobs() -> list[dict]:
    return read_json(JOBS_JSON, [])


def save_jobs(jobs: list[dict]) -> None:
    write_json(JOBS_JSON, jobs)


def get_job(job_id: str) -> Optional[dict]:
    jobs = list_jobs()
    return next((job for job in jobs if job["id"] == job_id), None)


def find_active_preview_job(game_id: str) -> Optional[dict]:
    jobs = list_jobs()
    for job in reversed(jobs):
        if (
            job.get("type") == "preview"
            and job.get("game_id") == game_id
            and job.get("status") in {"pending", "processing"}
        ):
            return job
    return None


def create_clip_job(
    game: dict,
    current_seconds: int,
    start_seconds: int,
    end_seconds: int,
    preset_name: str,
) -> dict:
    job = {
        "id": generate_id(),
        "type": "clip",
        "status": "pending",
        "created_at": utc_now(),
        "started_at": None,
        "finished_at": None,
        "error_message": None,
        "clip_id": None,
        "clip_file": None,
        "game_id": game["id"],
        "game_name": game["name"],
        "source_file": game["file_path"],
        "event_seconds": current_seconds,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "preset_name": preset_name,
    }

    append_json_item(JOBS_JSON, job)
    start_worker_if_needed()
    return job


def create_preview_job(game: dict) -> dict:
    existing_job = find_active_preview_job(game["id"])
    if existing_job:
        return existing_job

    job = {
        "id": generate_id(),
        "type": "preview",
        "status": "pending",
        "created_at": utc_now(),
        "started_at": None,
        "finished_at": None,
        "error_message": None,
        "game_id": game["id"],
        "game_name": game["name"],
        "source_file": game["file_path"],
        "preview_file": None,
    }

    append_json_item(JOBS_JSON, job)
    start_worker_if_needed()
    return job


def update_job(job_id: str, **fields) -> Optional[dict]:
    with _job_lock:
        jobs = list_jobs()
        updated = None

        for idx, job in enumerate(jobs):
            if job["id"] != job_id:
                continue

            jobs[idx] = {**job, **fields}
            updated = jobs[idx]
            break

        if updated is None:
            return None

        save_jobs(jobs)
        return updated


def save_clip_metadata(clip: dict) -> None:
    append_json_item(CLIPS_JSON, clip)


def process_clip_job(job: dict) -> None:
    clip = create_clip(
        game_id=job["game_id"],
        game_name=job["game_name"],
        source_file=job["source_file"],
        event_seconds=job["event_seconds"],
        start_seconds=job["start_seconds"],
        end_seconds=job["end_seconds"],
        preset_name=job["preset_name"],
    )

    save_clip_metadata(clip)

    update_job(
        job["id"],
        status="done",
        finished_at=utc_now(),
        clip_id=clip["id"],
        clip_file=clip["clip_file"],
    )


def process_preview_job(job: dict) -> None:
    preview_path = create_preview(job["source_file"])

    update_job(
        job["id"],
        status="done",
        finished_at=utc_now(),
        preview_file=str(preview_path),
    )


def process_next_pending_job() -> bool:
    with _job_lock:
        jobs = list_jobs()
        pending_job = next((job for job in jobs if job["status"] == "pending"), None)

        if not pending_job:
            return False

        pending_job_id = pending_job["id"]

        for idx, job in enumerate(jobs):
            if job["id"] == pending_job_id:
                jobs[idx] = {
                    **job,
                    "status": "processing",
                    "started_at": utc_now(),
                    "error_message": None,
                }
                pending_job = jobs[idx]
                break

        save_jobs(jobs)

    try:
        if pending_job["type"] == "clip":
            process_clip_job(pending_job)
        elif pending_job["type"] == "preview":
            process_preview_job(pending_job)
        else:
            raise RuntimeError(f"Tipo de job não suportado: {pending_job['type']}")
    except Exception as e:
        update_job(
            pending_job_id,
            status="error",
            finished_at=utc_now(),
            error_message=str(e),
        )

    return True


def worker_loop() -> None:
    global _worker_running

    try:
        while True:
            processed = process_next_pending_job()
            if not processed:
                break
    finally:
        with _worker_lock:
            _worker_running = False


def start_worker_if_needed() -> None:
    global _worker_running

    with _worker_lock:
        if _worker_running:
            return

        _worker_running = True

    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()