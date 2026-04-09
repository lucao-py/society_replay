import subprocess
from pathlib import Path

from src.config import PREVIEWS_DIR


def get_preview_path(source_video: Path) -> Path:
    return PREVIEWS_DIR / f"{source_video.stem}_preview.mp4"


def preview_exists(source_video: Path) -> bool:
    return get_preview_path(source_video).exists()


def create_preview(source_video: Path) -> Path:
    preview_path = get_preview_path(source_video)

    if preview_path.exists():
        return preview_path

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_video),
        "-vf",
        "scale=-2:480",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "32",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        str(preview_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not preview_path.exists():
        raise RuntimeError(f"Falha ao gerar preview.\n{result.stderr}")

    return preview_path