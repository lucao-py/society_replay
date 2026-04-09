from src.config import VIDEOS_DIR, PREVIEWS_DIR, CLIPS_DIR, METADATA_DIR, GAMES_JSON, CLIPS_JSON
from src.storage import ensure_dir, ensure_json_file


def main():
    ensure_dir(VIDEOS_DIR)
    ensure_dir(PREVIEWS_DIR)
    ensure_dir(CLIPS_DIR)
    ensure_dir(METADATA_DIR)

    ensure_json_file(GAMES_JSON, [])
    ensure_json_file(CLIPS_JSON, [])

    print("Estrutura criada com sucesso.")


if __name__ == "__main__":
    main()