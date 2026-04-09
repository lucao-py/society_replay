import subprocess
from datetime import datetime

from src.config import CLIPS_DIR
from src.utils import sanitize_filename, generate_id


def build_clip_name(game_name: str, start_seconds: int, end_seconds: int) -> str:
    safe_game_name = sanitize_filename(game_name)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{safe_game_name}_{start_seconds}_{end_seconds}_{ts}.mp4"


def create_clip(
    game_id: str,
    game_name: str,
    source_file: str,
    event_seconds: int,
    start_seconds: int,
    end_seconds: int,
    preset_name: str,
):
    duration = max(1, end_seconds - start_seconds)
    output_name = build_clip_name(game_name, start_seconds, end_seconds)
    output_path = CLIPS_DIR / output_name

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_seconds),
        "-i",
        source_file,
        "-t",
        str(duration),
        "-c",
        "copy",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not output_path.exists():
        fallback_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_seconds),
            "-i",
            source_file,
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            str(output_path),
        ]
        fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True)

        if fallback_result.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                "Falha ao gerar clip.\n"
                f"Comando 1 stderr:\n{result.stderr}\n\n"
                f"Comando 2 stderr:\n{fallback_result.stderr}"
            )

    return {
        "id": generate_id(),
        "game_id": game_id,
        "game_name": game_name,
        "source_file": source_file,
        "clip_file": str(output_path.resolve()),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "event_seconds": event_seconds,
        "created_at": datetime.utcnow().isoformat(),
        "preset_name": preset_name,
        "status": "ready",
    }