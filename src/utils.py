import re
from datetime import timedelta


def sanitize_filename(name: str, max_length: int = 80) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().replace(" ", "_")
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")
    return name or "audio"


def format_duration(seconds: int) -> str:
    return str(timedelta(seconds=seconds))
