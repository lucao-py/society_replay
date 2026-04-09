from pathlib import Path

from src.config import VIDEOS_DIR
from src.preview_service import create_preview
from src.game_service import sync_games_from_videos


def main():
    sync_games_from_videos()

    video_files = sorted(VIDEOS_DIR.iterdir())
    for file_path in video_files:
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".avi", ".m4v"}:
            continue

        print(f"Gerando preview: {file_path.name}")
        create_preview(Path(file_path))

    print("Previews gerados com sucesso.")


if __name__ == "__main__":
    main()