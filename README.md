# AudioFetch

Download audio from YouTube URLs as MP3 files.

## Installation

### Prerequisites - ffmpeg

**macOS**
```bash
brew install ffmpeg
```

**Ubuntu/Debian**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows**
```bash
winget install FFmpeg
```

### Install AudioFetch

```bash
# Clone or navigate to the project directory
cd audiofetch

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install the package (optional, for `audiofetch` command)
pip install -e .
```

## Usage

```bash
# Show help
audiofetch --help

# Download audio from a single YouTube URL
audiofetch download https://www.youtube.com/watch?v=VIDEO_ID

# Download multiple URLs from a file (one per line)
audiofetch batch urls.txt

# Show video metadata without downloading
audiofetch info https://www.youtube.com/watch?v=VIDEO_ID

# Show version
audiofetch version
```

### Run without installing

```bash
python -m src.main download <URL>
python -m src.main batch urls.txt
python -m src.main info <URL>
python -m src.main version
```

## API Server (for Chrome extension)

The API server exposes an endpoint that downloads/converts a YouTube URL and streams the resulting MP3 back to the client (the file is cleaned up after the response is sent).

### Run the server

```bash
cd audiofetch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the FastAPI server
uvicorn src.api_server:app --reload --port 8000
```

### Test the endpoint

```bash
curl -X POST "http://localhost:8000/api/download-mp3" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}' \
  --output out.mp3
```

## Chrome Extension (Manifest V3)

The extension injects a small floating **MP3** button on YouTube watch pages. Clicking it sends the current page URL to the local backend and triggers a browser download of the returned MP3.

### Load the extension

1) Start the backend server (see above).

2) In Chrome, open `chrome://extensions` and enable **Developer mode**.

3) Click **Load unpacked** and select the `chrome-extension/` folder at the repo root.

### Notes

- The extension is currently configured to call `http://localhost:8000/api/download-mp3`.
- You must have `ffmpeg` installed locally for conversions to work.

## Configuration

Copy `.env.example` to `.env` and customize:

| Variable                    | Default     | Description                         |
|-----------------------------|-------------|-------------------------------------|
| `DOWNLOAD_DIR`              | `downloads` | Directory for downloaded MP3 files  |
| `MAX_CONCURRENT_DOWNLOADS`  | `5`         | Maximum parallel downloads          |
| `RETRY_COUNT`               | `3`         | Retry attempts per failed download  |

## Logs

Logs are written to `logs/app.log` with rotation at 10 MB and 30-day retention.

## Project Structure

```
audiofetch/
├── src/
│   ├── main.py         CLI entry point (typer)
│   ├── downloader.py   AudioDownloader class (yt-dlp)
│   ├── config.py       Pydantic settings
│   ├── logger.py       Loguru configuration
│   ├── utils.py        Utility functions
│   └── models.py       Pydantic models
├── downloads/          Downloaded MP3 files
├── logs/               Application logs
├── .env.example        Configuration template
├── requirements.txt    Python dependencies
├── pyproject.toml      Project metadata
└── README.md           This file
```
