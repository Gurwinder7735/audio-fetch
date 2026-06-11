import asyncio
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import yt_dlp
from loguru import logger
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from src.config import Settings
from src.models import DownloadRecord, VideoInfo
from src.utils import sanitize_filename


class AudioDownloader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        self._executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_downloads + 2,
        )
        self._progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        )
        self._progress_active = False

    def start_progress(self) -> None:
        if not self._progress_active:
            self._progress.start()
            self._progress_active = True

    def stop_progress(self) -> None:
        if self._progress_active:
            self._progress.stop()
            self._progress_active = False

    @staticmethod
    def _check_dependencies() -> None:
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg not found. Install it:\n"
                "  macOS: brew install ffmpeg\n"
                "  Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  Windows: winget install FFmpeg"
            )

    async def get_info(self, url: str) -> VideoInfo:
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(
            self._executor,
            self._extract_info,
            url,
        )
        return VideoInfo(
            url=url,
            title=info.get("title", "Unknown"),
            duration=info.get("duration", 0),
            channel=info.get("channel") or info.get("uploader") or "Unknown",
            upload_date=info.get("upload_date"),
        )

    @staticmethod
    def _extract_info(url: str) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download_audio(self, url: str) -> DownloadRecord:
        record = DownloadRecord(url=url, start_time=datetime.now())
        task: TaskID | None = None

        async with self._semaphore:
            try:
                self._check_dependencies()

                info = await self.get_info(url)
                safe_title = sanitize_filename(info.title)
                mp3_path = self.settings.downloads_path / f"{safe_title}.mp3"

                if mp3_path.exists():
                    file_size = mp3_path.stat().st_size
                    if file_size > 0:
                        logger.info(f"Skipping {url} - file already exists: {mp3_path}")
                        record.file_path = mp3_path
                        record.success = True
                        record.reason = "Skipped - already exists"
                        return record

                display_title = (
                    f"{safe_title[:35]}..." if len(safe_title) > 35 else safe_title
                )
                task = self._progress.add_task(f"[cyan]{display_title}")

                loop = asyncio.get_running_loop()
                file_path = await loop.run_in_executor(
                    self._executor,
                    self._download_with_retry,
                    url,
                    safe_title,
                    task,
                )

                record.file_path = Path(file_path)
                record.success = True
                record.reason = "Success"
                logger.info(f"Downloaded: {url} -> {file_path}")

            except Exception as e:
                record.reason = self._user_friendly_error(e)
                logger.error(f"Failed to download {url}: {e}")

            finally:
                if task is not None:
                    self._progress.remove_task(task)
                record.end_time = datetime.now()
                if record.start_time and record.end_time:
                    record.duration_seconds = (
                        record.end_time - record.start_time
                    ).total_seconds()

            return record

    def _download_with_retry(self, url: str, title: str, task_id: TaskID) -> str:
        max_retries = self.settings.retry_count
        last_exception: Exception | None = None

        for attempt in range(1, max_retries + 2):
            try:
                return self._download_single(url, title, task_id)
            except Exception as e:
                last_exception = e
                if attempt <= max_retries:
                    wait = 1.0 * (2 ** (attempt - 1))
                    logger.warning(
                        f"Attempt {attempt}/{max_retries + 1} failed for {url}: {e}. "
                        f"Retrying in {wait:.1f}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"All {max_retries + 1} attempts failed for {url}: {e}"
                    )
                    raise

        raise last_exception  # type: ignore[union-attr]

    def _download_single(self, url: str, title: str, task_id: TaskID) -> str:
        output_template = str(self.settings.downloads_path / f"{title}.%(ext)s")

        def progress_hook(d: dict[str, Any]) -> None:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    pct = (downloaded / total) * 100
                    self._progress.update(task_id, completed=pct)
            elif d["status"] == "finished":
                self._progress.update(task_id, completed=100)

        opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                },
            ],
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "nooverwrites": True,
            "noplaylist": True,
            "progress_hooks": [progress_hook],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        return str(self.settings.downloads_path / f"{title}.mp3")

    @staticmethod
    def _user_friendly_error(error: Exception) -> str:
        msg = str(error)
        if "Private video" in msg:
            return "This video is private"
        if "removed" in msg.lower() or "deleted" in msg.lower():
            return "This video has been removed"
        if "age" in msg.lower() and (
            "restrict" in msg.lower() or "block" in msg.lower()
        ):
            return "This video is age-restricted"
        if "ffmpeg" in msg.lower() or "ffprobe" in msg.lower():
            return "ffmpeg is not installed. See README for instructions"
        if "HTTP Error 404" in msg:
            return "Video not found (404)"
        if "HTTP Error 410" in msg:
            return "Video has been removed (410)"
        if "HTTP Error" in msg:
            return "Network error while accessing the video"
        if "Unable to extract" in msg:
            return "Could not extract video information. The URL may be invalid"
        if "Unsupported URL" in msg:
            return "The URL is not supported"
        if "Video unavailable" in msg:
            return "This video is unavailable"
        if "Sign in" in msg:
            return "This video requires sign-in"
        if "Copyright" in msg or "copyright" in msg:
            return "This video is unavailable due to copyright claim"
        return msg.split("\n")[0] if "\n" in msg else msg

    async def download_batch(self, urls: list[str]) -> list[DownloadRecord]:
        tasks = [self.download_audio(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        records: list[DownloadRecord] = []
        for result in results:
            if isinstance(result, DownloadRecord):
                records.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Unexpected batch error: {result}")
        return records
