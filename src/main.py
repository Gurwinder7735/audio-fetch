import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console

from src import __version__
from src.config import Settings
from src.downloader import AudioDownloader
from src.logger import setup_logger
from src.utils import format_duration

console = Console()
settings = Settings()
app = typer.Typer(
    name="audiofetch",
    help="Download audio from YouTube URLs as MP3 files.",
)


def get_downloader() -> AudioDownloader:
    return AudioDownloader(settings)


@app.command()
def download(url: str) -> None:
    """Download audio from a single YouTube URL."""
    downloader = get_downloader()
    downloader.start_progress()
    try:
        record = asyncio.run(downloader.download_audio(url))
    finally:
        downloader.stop_progress()

    if record.success:
        console.print(f"[green]Downloaded:[/] {record.file_path}")
    else:
        console.print(f"[red]Failed:[/] {record.reason}")
        raise typer.Exit(code=1)


@app.command()
def batch(urls_file: Path) -> None:
    """Download audio from multiple URLs listed in a file (one per line)."""
    urls = urls_file.read_text().strip().splitlines()
    urls = [u.strip() for u in urls if u.strip() and not u.startswith("#")]

    if not urls:
        console.print("[red]No URLs found in the file[/]")
        raise typer.Exit(code=1)

    console.print(f"Processing [cyan]{len(urls)}[/] URL(s)...")

    downloader = get_downloader()
    downloader.start_progress()
    try:
        records = asyncio.run(downloader.download_batch(urls))
    finally:
        downloader.stop_progress()

    total = len(records)
    successful = [r for r in records if r.success]
    failed = [r for r in records if not r.success]

    console.print()
    console.print(f"[green]Successful:[/] {len(successful)}/{total}")
    if failed:
        console.print(f"[red]Failed:[/] {len(failed)}/{total}")
        console.print()
        for rec in failed:
            console.print(f"  [red]✗[/] {rec.url}")
            console.print(f"    [dim]Reason:[/] {rec.reason}")


@app.command(name="from-json")
def from_json(json_file: Path) -> None:
    """Download audio from URLs stored in a JSON file.

    Accepts a JSON array of strings, or an array of objects with a 'url' key.
    """
    raw = json.loads(json_file.read_text(encoding="utf-8"))

    if isinstance(raw, dict):
        raw = raw.get("urls", raw.get("videos", []))

    urls: list[str] = []
    for item in raw:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict) and "url" in item:
            urls.append(item["url"])

    if not urls:
        console.print("[red]No URLs found in the JSON file[/]")
        raise typer.Exit(code=1)

    console.print(f"Processing [cyan]{len(urls)}[/] URL(s) from JSON...")

    downloader = get_downloader()
    downloader.start_progress()
    try:
        records = asyncio.run(downloader.download_batch(urls))
    finally:
        downloader.stop_progress()

    total = len(records)
    successful = [r for r in records if r.success]
    failed = [r for r in records if not r.success]

    console.print()
    console.print(f"[green]Successful:[/] {len(successful)}/{total}")
    if failed:
        console.print(f"[red]Failed:[/] {len(failed)}/{total}")
        console.print()
        for rec in failed:
            console.print(f"  [red]✗[/] {rec.url}")
            console.print(f"    [dim]Reason:[/] {rec.reason}")


@app.command()
def info(url: str) -> None:
    """Display video metadata without downloading."""
    downloader = get_downloader()
    try:
        video_info = asyncio.run(downloader.get_info(url))
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(code=1)

    from rich.table import Table

    table = Table(title="Video Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Title", video_info.title)
    table.add_row("Duration", format_duration(video_info.duration))
    table.add_row("Channel", video_info.channel)
    if video_info.upload_date:
        table.add_row("Upload Date", video_info.upload_date)

    console.print(table)


@app.command()
def version() -> None:
    """Display the application version."""
    console.print(f"AudioFetch v{__version__}")


def main() -> None:
    setup_logger()
    app()


if __name__ == "__main__":
    main()
