from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MediaType(Enum):
    AUTO = "auto"
    TV = "tv"
    MOVIE = "movie"
    MUSIC = "music"


class TitleLanguage(Enum):
    AUTO = "auto"
    PT_BR = "pt-BR"
    ORIGINAL = "original"


@dataclass
class RenameConfig:
    media_type: MediaType
    language: TitleLanguage
    show_hidden: bool = False


@dataclass
class RenameOperation:
    source: Path
    destination: Path
    subtitle_source: Path | None = None
    subtitle_destination: Path | None = None
    status: str = "ready"
    message: str = ""
