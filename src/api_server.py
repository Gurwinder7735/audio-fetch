import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from src.config import Settings
from src.downloader import AudioDownloader


class DownloadMp3Request(BaseModel):
    url: str


def _cleanup_download(file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    finally:
        parent = file_path.parent
        try:
            parent.rmdir()
        except OSError:
            pass


def _ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "ffmpeg not found. Install it:\n"
                "  macOS: brew install ffmpeg\n"
                "  Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  Windows: winget install FFmpeg"
            ),
        )


app = FastAPI(title="AudioFetch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/download-mp3")
async def download_mp3(payload: DownloadMp3Request) -> FileResponse:
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url'")

    _ensure_ffmpeg()

    tmp_dir = Path("downloads") / "_tmp" / str(uuid.uuid4())
    settings = Settings(
        download_dir=tmp_dir,
        max_concurrent_downloads=1,
    )
    downloader = AudioDownloader(settings)

    record = await downloader.download_audio(url)
    if not record.success or record.file_path is None:
        raise HTTPException(status_code=500, detail=record.reason or "Download failed")

    file_path = record.file_path
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Output file missing after download")

    filename = file_path.name
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(_cleanup_download, file_path),
    )


@app.get("/api/download-mp3")
async def download_mp3_get(url: str = Query(..., min_length=1)) -> FileResponse:
    """
    GET variant for browser/extension downloads.
    Lets Chrome download directly via a URL (no fetch->blob needed).
    """
    return await download_mp3(DownloadMp3Request(url=url))

