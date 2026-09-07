# Society Replay

A web application for reviewing recorded videos and generating precise clips, combining Google Drive synchronization, browser-based playback, background processing, and FFmpeg-based video extraction.

## Overview

Society Replay simplifies the process of reviewing long recordings and extracting specific moments without manually handling the original video files.

Videos are synchronized from Google Drive and processed through the following workflow:

```text
Google Drive
    ↓
Video Synchronization
    ↓
Local Video Storage
    ↓
FFmpeg Preview Generation
    ↓
Browser Video Player
    ↓
Start / End Selection
    ↓
Background Processing
    ↓
FFmpeg Clip Generation
    ↓
Preview / Download
```

The application generates lightweight video previews for browser playback while keeping the original files available for clip extraction.

Video, preview, clip, and processing-job metadata are persisted locally using JSON files.

## Clip Generation

The editor allows the user to navigate through a video, mark the beginning and end of a segment, and generate a downloadable MP4 clip.

Preview and clip generation are handled as background jobs so video processing does not block the main web interface.

## Running the Project

FFmpeg must be installed and available in the system path.

Clone the repository and install the dependencies:

```bash
git clone https://github.com/lucao-py/society_replay.git
cd society_replay

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

Configure the Google Drive integration in a `.env` file:

```env
GOOGLE_DRIVE_FOLDER_ID=<drive-folder-id>
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
```

Place the Google service account credentials in `service_account.json` and ensure the service account has access to the configured Drive folder.

Start the application:

```bash
python app.py
```

The application runs on port `5000`.

## Stack

Python, Flask, FFmpeg, Google Drive API, JavaScript, HTML and CSS.
