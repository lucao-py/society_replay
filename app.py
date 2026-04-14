from pathlib import Path
import os
import threading
import shutil
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, flash, jsonify
from datetime import datetime

def setup_google_credentials():
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not raw_json:
        return

    cred_path = Path("/tmp/service_account.json")
    cred_path.write_text(raw_json, encoding="utf-8")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = str(cred_path)

setup_google_credentials()


from src.config import (
    VIDEOS_DIR,
    PREVIEWS_DIR,
    CLIPS_DIR,
    METADATA_DIR,
    GAMES_JSON,
    CLIPS_JSON,
    JOBS_JSON,
    PRESET_BEFORE,
    PRESET_AFTER,
)
from src.storage import ensure_dir, ensure_json_file, read_json, write_json
from src.game_service import sync_games_from_videos, list_games, get_game_by_id
from src.drive_sync_service import sync_videos_from_drive
from src.utils import format_seconds
from src.preview_service import get_preview_path, preview_exists
from src.job_service import create_clip_job, create_preview_job, get_job



app = Flask(__name__)

SYNC_STATUS = {
    "status": "idle",
    "message": "Nenhuma sincronização em andamento.",
    "started_at": None,
    "finished_at": None,
    "result": {
        "downloaded": 0,
        "skipped": 0,
        "ignored": 0,
    },
    "error": None,
}

def ensure_storage():
    for path in [VIDEOS_DIR, PREVIEWS_DIR, CLIPS_DIR, METADATA_DIR]:
        Path(path).mkdir(parents=True, exist_ok=True)

    if not GAMES_JSON.exists():
        GAMES_JSON.write_text("[]", encoding="utf-8")

    if not CLIPS_JSON.exists():
        CLIPS_JSON.write_text("[]", encoding="utf-8")

    if not JOBS_JSON.exists():
        JOBS_JSON.write_text("[]", encoding="utf-8")



ensure_storage()
app.secret_key = "replay-society-secret-key"

def run_sync():
    global SYNC_STATUS

    try:
        SYNC_STATUS = {
            "status": "processing",
            "message": "Sincronização em andamento...",
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
            "result": {
                "downloaded": 0,
                "skipped": 0,
                "ignored": 0,
            },
            "error": None,
        }

        result = sync_videos_from_drive()
        sync_games_from_videos()

        downloaded_count = len(result["downloaded"])
        skipped_count = len(result["skipped"])
        ignored_count = len(result["ignored"])

        SYNC_STATUS = {
            "status": "done",
            "message": "Sincronização concluída com sucesso.",
            "started_at": SYNC_STATUS["started_at"],
            "finished_at": datetime.utcnow().isoformat(),
            "result": {
                "downloaded": downloaded_count,
                "skipped": skipped_count,
                "ignored": ignored_count,
            },
            "error": None,
        }

        print(
            f"[SYNC] Concluído | novos: {downloaded_count}, "
            f"existentes: {skipped_count}, ignorados: {ignored_count}"
        )

    except Exception as e:
        SYNC_STATUS = {
            "status": "error",
            "message": "Erro na sincronização.",
            "started_at": SYNC_STATUS.get("started_at"),
            "finished_at": datetime.utcnow().isoformat(),
            "result": {
                "downloaded": 0,
                "skipped": 0,
                "ignored": 0,
            },
            "error": str(e),
        }

        print(f"[SYNC ERROR] {e}")


def bootstrap():
    ensure_dir(VIDEOS_DIR)
    ensure_dir(PREVIEWS_DIR)
    ensure_dir(CLIPS_DIR)
    ensure_dir(METADATA_DIR)
    ensure_json_file(GAMES_JSON, [])
    ensure_json_file(CLIPS_JSON, [])
    ensure_json_file(JOBS_JSON, [])


bootstrap()
sync_games_from_videos()


@app.route("/")
def index():
    games = list_games()
    return render_template("index.html", games=games)


@app.route("/sync-drive", methods=["POST"])
def sync_drive():
    if SYNC_STATUS["status"] == "processing":
        return jsonify({
            "ok": False,
            "message": "Já existe uma sincronização em andamento."
        }), 409

    thread = threading.Thread(target=run_sync, daemon=True)
    thread.start()

    return jsonify({
        "ok": True,
        "status": "processing",
        "message": "Sincronização iniciada."
    }), 202

@app.route("/sync-status")
def sync_status():
    return jsonify({
        "ok": True,
        "sync": SYNC_STATUS
    })

@app.route("/video/<game_id>")
def video_page(game_id):
    game = get_game_by_id(game_id)
    if not game:
        abort(404)

    master_video_path = Path(game["file_path"]).resolve()
    preview_ready = preview_exists(master_video_path)

    latest_clip = None
    clips = read_json(CLIPS_JSON, [])
    matching = [c for c in clips if c["game_id"] == game_id]
    if matching:
        latest_clip = matching[-1]

    preview_url = None
    preview_version = None

    if preview_ready:
        preview_path = get_preview_path(master_video_path)
        preview_url = url_for("serve_preview", game_id=game_id)
        preview_version = int(preview_path.stat().st_mtime)

    return render_template(
        "video.html",
        game=game,
        preview_ready=preview_ready,
        preview_url=preview_url,
        preview_version=preview_version,
        latest_clip=latest_clip,
        preset_before=PRESET_BEFORE,
        preset_after=PRESET_AFTER,
    )


@app.route("/generate_clip/<game_id>", methods=["POST"])
def generate_clip(game_id):
    game = get_game_by_id(game_id)
    if not game:
        abort(404)

    data = request.get_json(silent=True) or request.form

    current_seconds = int(float(data.get("current_seconds", 0) or 0))

    raw_start = data.get("start_seconds")
    raw_end = data.get("end_seconds")

    start_seconds = None
    end_seconds = None

    if raw_start not in (None, "", "null") and raw_end not in (None, "", "null"):
        start_seconds = int(float(raw_start))
        end_seconds = int(float(raw_end))

        if end_seconds < start_seconds:
            start_seconds, end_seconds = end_seconds, start_seconds

    if start_seconds is None or end_seconds is None or end_seconds <= start_seconds:
        start_seconds = max(0, current_seconds - PRESET_BEFORE)
        end_seconds = current_seconds + PRESET_AFTER
        preset_name = f"{PRESET_BEFORE}s antes + {PRESET_AFTER}s depois"
    else:
        preset_name = "trecho manual"

    job = create_clip_job(
        game=game,
        current_seconds=current_seconds,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        preset_name=preset_name,
    )

    return jsonify(
        {
            "ok": True,
            "job_id": job["id"],
            "status": job["status"],
            "message": "Geração de clipe iniciada.",
        }
    ), 202

@app.route("/clip-status/<job_id>")
def clip_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"ok": False, "message": "Job não encontrado."}), 404

    return jsonify(
        {
            "ok": True,
            "job_id": job["id"],
            "status": job["status"],
            "error_message": job.get("error_message"),
            "clip_id": job.get("clip_id"),
            "clip_file": job.get("clip_file"),
        }
    )

@app.route("/latest_clip/<game_id>")
def latest_clip(game_id):
    clips = read_json(CLIPS_JSON, [])
    matching = [c for c in clips if c["game_id"] == game_id]

    if not matching:
        return jsonify({"ok": False, "message": "Nenhum clipe encontrado."}), 404

    clip = matching[-1]

    return jsonify(
        {
            "ok": True,
            "clip": {
                "id": clip["id"],
                "download_url": url_for("download_clip", clip_id=clip["id"]),
            }
        }
    )

@app.route("/admin/clear-previews", methods=["POST"])
def clear_previews():
    try:
        if PREVIEWS_DIR.exists():
            shutil.rmtree(PREVIEWS_DIR)

        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

        return jsonify({
            "ok": True,
            "message": "Previews apagados com sucesso."
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"Erro ao apagar previews: {e}"
        }), 500


@app.route("/admin/regenerate-previews", methods=["POST"])
def regenerate_previews():
    try:
        games = list_games()
        created_jobs = 0

        for game in games:
            source_file = Path(game["file_path"])
            if not source_file.exists():
                continue

            preview_path = get_preview_path(source_file.resolve())
            if preview_path.exists():
                preview_path.unlink()

            create_preview_job(game)
            created_jobs += 1

        return jsonify({
            "ok": True,
            "message": f"Regeneração iniciada para {created_jobs} vídeo(s).",
            "jobs_created": created_jobs,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"Erro ao regenerar previews: {e}"
        }), 500
    
@app.route("/admin/delete-video/<game_id>", methods=["POST"])
def delete_video(game_id):
    try:
        game = get_game_by_id(game_id)
        if not game:
            return jsonify({
                "ok": False,
                "message": "Vídeo não encontrado."
            }), 404

        source_file = Path(game["file_path"])
        preview_path = get_preview_path(source_file.resolve())

        if source_file.exists():
            source_file.unlink()

        if preview_path.exists():
            preview_path.unlink()

        games = read_json(GAMES_JSON, [])
        games = [g for g in games if g["id"] != game_id]
        write_json(GAMES_JSON, games)

        clips = read_json(CLIPS_JSON, [])
        clips_to_remove = [c for c in clips if c["game_id"] == game_id]

        for clip in clips_to_remove:
            clip_path = Path(clip["clip_file"])
            if clip_path.exists():
                clip_path.unlink()

        clips = [c for c in clips if c["game_id"] != game_id]
        write_json(CLIPS_JSON, clips)

        return jsonify({
            "ok": True,
            "message": f"Vídeo '{game['file_name']}' removido com sucesso."
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"Erro ao deletar vídeo: {e}"
        }), 500
    
@app.route("/admin/clear-clips", methods=["POST"])
def clear_clips():
    try:
        if CLIPS_DIR.exists():
            for file_path in CLIPS_DIR.iterdir():
                if file_path.is_file():
                    file_path.unlink()

        write_json(CLIPS_JSON, [])

        return jsonify({
            "ok": True,
            "message": "Todos os clipes foram removidos com sucesso."
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"Erro ao limpar clipes: {e}"
        }), 500   
@app.route("/media/preview/<game_id>")
def serve_preview(game_id):
    game = get_game_by_id(game_id)
    if not game:
        abort(404)

    preview_path = get_preview_path(Path(game["file_path"]).resolve())
    if not preview_path.exists():
        abort(404)

    return send_from_directory(
        PREVIEWS_DIR,
        preview_path.name,
        mimetype="video/mp4",
        conditional=True,
        max_age=3600,
    )
@app.route("/generate_preview/<game_id>", methods=["POST"])
def generate_preview(game_id):
    game = get_game_by_id(game_id)
    if not game:
        return jsonify({"ok": False, "message": "Jogo não encontrado."}), 404

    source_file = Path(game["file_path"]).resolve()
    if preview_exists(source_file):
        return jsonify(
            {
                "ok": True,
                "already_ready": True,
                "preview_url": url_for("serve_preview", game_id=game_id),
            }
        )

    job = create_preview_job(game)

    return jsonify(
        {
            "ok": True,
            "already_ready": False,
            "job_id": job["id"],
            "status": job["status"],
            "message": "Geração de preview iniciada.",
        }
    ), 202

@app.route("/preview-status/<job_id>")
def preview_status(job_id):
    job = get_job(job_id)
    if not job or job.get("type") != "preview":
        return jsonify({"ok": False, "message": "Job de preview não encontrado."}), 404

    if job["status"] == "done":
        preview_path = get_preview_path(Path(job["source_file"]).resolve())
        preview_version = int(preview_path.stat().st_mtime) if preview_path.exists() else int(datetime.utcnow().timestamp())

        return jsonify(
            {
                "ok": True,
                "job_id": job["id"],
                "status": job["status"],
                "preview_url": url_for("serve_preview", game_id=job["game_id"]),
                "preview_version": preview_version,
            }
        )

    return jsonify(
        {
            "ok": True,
            "job_id": job["id"],
            "status": job["status"],
            "error_message": job.get("error_message"),
        }
    )

@app.route("/download_clip/<clip_id>")
def download_clip(clip_id):
    clips = read_json(CLIPS_JSON, [])
    clip = next((c for c in clips if c["id"] == clip_id), None)

    if not clip:
        abort(404)

    clip_path = Path(clip["clip_file"])
    if not clip_path.exists():
        abort(404)

    return send_from_directory(
        CLIPS_DIR,
        clip_path.name,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=clip_path.name,
        conditional=True,
        max_age=3600,
    )

@app.context_processor
def inject_helpers():
    return {"format_seconds": format_seconds}

@app.after_request
def add_cache_headers(response):
    if request.path.startswith("/media/preview/") or request.path.startswith("/download_clip/"):
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)