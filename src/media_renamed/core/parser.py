import re
from pathlib import Path

from .models import MediaType


VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".m4v",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".ogg",
    ".opus",
}

EPISODE_PATTERN = re.compile(
    r"(?:[sS](\d{1,2})[eE](\d{1,2}))"
    r"|"
    r"(\d{1,2})[xX](\d{1,2})"
)


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def extract_episode(filename: str) -> tuple[int, int] | None:
    match = EPISODE_PATTERN.search(filename)

    if not match:
        return None

    if match.group(1):
        return int(match.group(1)), int(match.group(2))

    return int(match.group(3)), int(match.group(4))


def extract_series_name(filename: str) -> str | None:
    match = EPISODE_PATTERN.search(filename)

    if not match:
        return None

    name = filename[:match.start()]
    name = re.sub(r"[\._-]+", " ", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip() or None


def extract_movie_name(filename: str) -> str:
    name = Path(filename).stem

    name = re.sub(
        r"\b(2160p|1080p|720p|480p|4k|"
        r"WEB-DL|WEBRip|BluRay|BRRip|"
        r"HDTV|HDR|x264|x265|HEVC|"
        r"AAC|DTS|REMUX)\b",
        " ",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(r"[._-]+", " ", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def detect_media_type(path: Path) -> MediaType:
    if is_audio(path):
        return MediaType.MUSIC

    if is_video(path):
        if extract_episode(path.name):
            return MediaType.TV

        return MediaType.MOVIE

    return MediaType.AUTO
