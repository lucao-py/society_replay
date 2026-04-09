from datetime import datetime

from src.config import VIDEOS_DIR, GAMES_JSON
from src.storage import read_json, write_json
from src.utils import generate_id

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


def sync_games_from_videos():
    existing = read_json(GAMES_JSON, [])
    existing_by_file = {item["file_name"]: item for item in existing}

    all_games = []

    for file_path in sorted(VIDEOS_DIR.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        if file_path.name in existing_by_file:
            all_games.append(existing_by_file[file_path.name])
        else:
            game = {
                "id": generate_id(),
                "name": file_path.stem,
                "file_name": file_path.name,
                "file_path": str(file_path.resolve()),
                "created_at": datetime.utcnow().isoformat(),
            }
            all_games.append(game)

    write_json(GAMES_JSON, all_games)
    return all_games


def list_games():
    return read_json(GAMES_JSON, [])


def get_game_by_id(game_id: str):
    for game in list_games():
        if game["id"] == game_id:
            return game
    return None