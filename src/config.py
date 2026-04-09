from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

VIDEOS_DIR = DATA_DIR / "videos"
PREVIEWS_DIR = DATA_DIR / "previews"
CLIPS_DIR = DATA_DIR / "clips"
METADATA_DIR = DATA_DIR / "metadata"

GAMES_JSON = METADATA_DIR / "games.json"
CLIPS_JSON = METADATA_DIR / "clips.json"

PRESET_BEFORE = 30
PRESET_AFTER = 10

# 🔥 ESSAS LINHAS QUE ESTÃO FALTANDO NO SEU
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(BASE_DIR / "service_account.json"),
)