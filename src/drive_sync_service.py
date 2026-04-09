import io
from pathlib import Path
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config import (
    VIDEOS_DIR,
    GOOGLE_DRIVE_FOLDER_ID,
    GOOGLE_SERVICE_ACCOUNT_FILE,
)
from src.preview_service import create_preview
from src.game_service import sync_games_from_videos

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


def _build_drive_service():
    if not GOOGLE_DRIVE_FOLDER_ID:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID não configurado no .env")

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    if not service_account_file:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_FILE não definido no .env")

    service_account_path = Path(service_account_file)
    
    if not service_account_path.exists():
        raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {service_account_path}")
    
    creds = Credentials.from_service_account_file(
        str(service_account_path),
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


def sync_videos_from_drive():
    service = _build_drive_service()

    results = service.files().list(
        q=f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name, modifiedTime)",
        pageSize=100,
        orderBy="modifiedTime desc",
    ).execute()

    files = results.get("files", [])

    downloaded = []
    skipped = []
    ignored = []
    previews_created = []

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        suffix = Path(file_name).suffix.lower()

        if suffix not in VIDEO_EXTENSIONS:
            ignored.append(file_name)
            continue

        local_path = VIDEOS_DIR / file_name

        if local_path.exists():
            skipped.append(file_name)
            continue

        request = service.files().get_media(fileId=file_id)

        with io.FileIO(local_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        downloaded.append(file_name)

        create_preview(local_path)
        previews_created.append(file_name)

    sync_games_from_videos()

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "ignored": ignored,
        "previews_created": previews_created,
        "total_found": len(files),
    }