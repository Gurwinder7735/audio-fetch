from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class VideoInfo(BaseModel):
    url: str
    title: str
    duration: int
    channel: str
    upload_date: str | None = None


class DownloadRecord(BaseModel):
    url: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float | None = None
    file_path: Path | None = None
    success: bool = False
    reason: str | None = None
