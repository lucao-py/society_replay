from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, send_file, abort, flash

from src.config import (
    VIDEOS_DIR,
    PREVIEWS_DIR,
    CLIPS_DIR,
    METADATA_DIR,
    GAMES_JSON,
    CLIPS_JSON,
    PRESET_BEFORE,
    PRESET_AFTER,
)
from src.storage import ensure_dir, ensure_json_file, read_json, write_json
from src.game_service import sync_games_from_videos, list_games, get_game_by_id
from src.preview_service import get_preview_path, create_preview
from src.ffmpeg_service import create_clip
from src.drive_sync_service import sync_videos_from_drive
from src.utils import format_seconds

app = Flask(__name__)

def ensure_storage():
    for path in [VIDEOS_DIR, PREVIEWS_DIR, CLIPS_DIR, METADATA_DIR]:
        Path(path).mkdir(parents=True, exist_ok=True)

    if not GAMES_JSON.exists():
        GAMES_JSON.write_text("[]", encoding="utf-8")

    if not CLIPS_JSON.exists():
        CLIPS_JSON.write_text("[]", encoding="utf-8")

ensure_storage()
app.secret_key = "replay-society-secret-key"




def bootstrap():
    ensure_dir(VIDEOS_DIR)
    ensure_dir(PREVIEWS_DIR)
    ensure_dir(CLIPS_DIR)
    ensure_dir(METADATA_DIR)
    ensure_json_file(GAMES_JSON, [])
    ensure_json_file(CLIPS_JSON, [])


def save_clip_metadata(clip: dict):
    clips = read_json(CLIPS_JSON, [])
    clips.append(clip)
    write_json(CLIPS_JSON, clips)


bootstrap()
sync_games_from_videos()


@app.route("/")
def index():
    sync_games_from_videos()
    games = list_games()
    return render_template("index.html", games=games)


@app.route("/sync-drive", methods=["POST"])
def sync_drive():
    try:
        result = sync_videos_from_drive()

        downloaded_count = len(result["downloaded"])
        skipped_count = len(result["skipped"])
        ignored_count = len(result["ignored"])

        flash(
            f"Sincronização concluída. "
            f"Novos vídeos: {downloaded_count}, "
            f"já existentes: {skipped_count}, "
            f"ignorados: {ignored_count}.",
            "success",
        )

    except Exception as e:
        flash(f"Erro ao sincronizar vídeos do Drive: {str(e)}", "error")

    return redirect(url_for("index"))


@app.route("/video/<game_id>")
def video_page(game_id):
    game = get_game_by_id(game_id)
    if not game:
        abort(404)

    master_video_path = Path(game["file_path"]).resolve()
    preview_path = get_preview_path(master_video_path)

    if not preview_path.exists():
        create_preview(master_video_path)

    latest_clip = None
    clips = read_json(CLIPS_JSON, [])
    matching = [c for c in clips if c["game_id"] == game_id]
    if matching:
        latest_clip = matching[-1]

    return render_template(
        "video.html",
        game=game,
        preview_url=url_for("serve_preview", game_id=game_id),
        latest_clip=latest_clip,
        preset_before=PRESET_BEFORE,
        preset_after=PRESET_AFTER,
    )


@app.route("/generate_clip/<game_id>", methods=["POST"])
def generate_clip(game_id):
    game = get_game_by_id(game_id)
    if not game:
        abort(404)

    current_seconds = int(float(request.form.get("current_seconds", 0) or 0))

    raw_start = request.form.get("start_seconds")
    raw_end = request.form.get("end_seconds")

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

    clip = create_clip(
        game_id=game["id"],
        game_name=game["name"],
        source_file=game["file_path"],
        event_seconds=current_seconds,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        preset_name=preset_name,
    )
    save_clip_metadata(clip)

    return redirect(url_for("video_page", game_id=game_id, clip_id=clip["id"]))


@app.route("/media/preview/<game_id>")
def serve_preview(game_id):
    game = get_game_by_id(game_id)
    if not game:
        abort(404)

    preview_path = get_preview_path(Path(game["file_path"]).resolve())
    if not preview_path.exists():
        create_preview(Path(game["file_path"]).resolve())

    return send_file(preview_path, mimetype="video/mp4", conditional=True)


@app.route("/download_clip/<clip_id>")
def download_clip(clip_id):
    clips = read_json(CLIPS_JSON, [])
    clip = next((c for c in clips if c["id"] == clip_id), None)

    if not clip:
        abort(404)

    clip_path = Path(clip["clip_file"])
    if not clip_path.exists():
        abort(404)

    return send_file(clip_path, mimetype="video/mp4", as_attachment=True, download_name=clip_path.name)


@app.context_processor
def inject_helpers():
    return {"format_seconds": format_seconds}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)