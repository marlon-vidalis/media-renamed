from pathlib import Path


SUBTITLE_EXTENSIONS = {
    ".srt",
    ".sub",
    ".ass",
    ".ssa",
    ".vtt",
}


def find_subtitle(video: Path) -> Path | None:
    for extension in SUBTITLE_EXTENSIONS:
        subtitle = video.with_suffix(extension)

        if subtitle.exists():
            return subtitle

    return None


def rename_media(
    source: Path,
    destination: Path,
    subtitle: Path | None = None,
) -> None:

    if destination.exists() and destination != source:
        raise FileExistsError(
            f"Destino já existe: {destination.name}"
        )

    subtitle_destination = None

    if subtitle:
        subtitle_destination = destination.with_suffix(
            subtitle.suffix
        )

        if (
            subtitle_destination.exists()
            and subtitle_destination != subtitle
        ):
            raise FileExistsError(
                f"Destino da legenda já existe: "
                f"{subtitle_destination.name}"
            )

    source.rename(destination)

    try:
        if subtitle and subtitle_destination:
            subtitle.rename(subtitle_destination)
    except Exception:
        if destination.exists() and not source.exists():
            destination.rename(source)

        raise
