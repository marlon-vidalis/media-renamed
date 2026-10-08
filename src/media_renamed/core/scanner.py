import re
from difflib import SequenceMatcher
from pathlib import Path

from ..api.tmdb import TMDBClient, normalize_language
from .models import (
    MediaType,
    RenameConfig,
    RenameOperation,
    TitleLanguage,
)
from .parser import (
    detect_media_type,
    extract_episode,
    extract_movie_name,
    extract_series_name,
    is_audio,
    is_video,
)
from .renamer import find_subtitle


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúàâêôãõçü ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(
        None,
        normalize_text(a),
        normalize_text(b),
    ).ratio()


def clean_title(title: str) -> str:
    title = title.replace(":", "")
    title = title.replace("/", " - ")
    title = re.sub(r"\s+", " ", title)
    return title.strip()


class MediaScanner:
    def __init__(self, client: TMDBClient):
        self.client = client

    def scan(
        self,
        folder: Path,
        config: RenameConfig,
    ) -> list[RenameOperation]:
        operations = []

        for path in sorted(
            folder.iterdir(),
            key=lambda p: p.name.lower(),
        ):
            if not path.is_file():
                continue

            if path.name.startswith(".") and not config.show_hidden:
                continue

            operation = self._process_file(path, config)

            if operation:
                operations.append(operation)

        return operations

    def _process_file(
        self,
        source: Path,
        config: RenameConfig,
    ) -> RenameOperation | None:

        detected_type = detect_media_type(source)

        media_type = (
            detected_type
            if config.media_type == MediaType.AUTO
            else config.media_type
        )

        if media_type == MediaType.MUSIC:
            if not is_audio(source):
                return None

            return RenameOperation(
                source=source,
                destination=source,
                status="unsupported",
                message="API de música ainda não configurada.",
            )

        if not is_video(source):
            return None

        if media_type == MediaType.TV:
            return self._process_tv(source, config)

        if media_type == MediaType.MOVIE:
            return self._process_movie(source, config)

        return None

    def _process_tv(
        self,
        source: Path,
        config: RenameConfig,
    ) -> RenameOperation:

        episode = extract_episode(source.name)
        series_name = extract_series_name(source.name)

        if not episode or not series_name:
            return RenameOperation(
                source=source,
                destination=source,
                status="invalid",
                message="Não foi possível identificar série/episódio.",
            )

        season, episode_number = episode

        results = self.client.search_tv(
            series_name,
            language="pt-BR",
        ).get("results", [])

        result = self._best_match(series_name, results)

        if not result:
            return RenameOperation(
                source=source,
                destination=source,
                status="not_found",
                message=f"Série não encontrada: {series_name}",
            )

        series_id = result["id"]

        original_language = normalize_language(
            result.get("original_language", "en")
        )

        language = (
            original_language
            if config.language == TitleLanguage.ORIGINAL
            else "pt-BR"
        )

        series = self.client.get_tv(
            series_id,
            language=language,
        )

        episode_data = self.client.get_episode(
            series_id,
            season,
            episode_number,
            language=language,
        )

        if config.language == TitleLanguage.ORIGINAL:
            series_title = series.get(
                "original_name",
                series.get("name", series_name),
            )
        else:
            series_title = series.get(
                "name",
                series.get("original_name", series_name),
            )

        episode_title = episode_data.get(
            "name",
            f"Episódio {episode_number}",
        )

        series_title = clean_title(series_title)
        episode_title = clean_title(episode_title)

        destination = source.with_name(
            f"{series_title} - "
            f"S{season:02d}E{episode_number:02d} - "
            f"{episode_title}"
            f"{source.suffix.lower()}"
        )

        return self._build_operation(
            source,
            destination,
        )

    def _process_movie(
        self,
        source: Path,
        config: RenameConfig,
    ) -> RenameOperation:

        movie_name = extract_movie_name(source.name)

        results = self.client.search_movie(
            movie_name,
            language="pt-BR",
        ).get("results", [])

        result = self._best_match(
            movie_name,
            results,
        )

        if not result:
            return RenameOperation(
                source=source,
                destination=source,
                status="not_found",
                message=f"Filme não encontrado: {movie_name}",
            )

        movie_id = result["id"]

        movie = self.client.get_movie(
            movie_id,
            language="pt-BR",
        )

        if config.language == TitleLanguage.ORIGINAL:
            title = movie.get(
                "original_title",
                movie.get("title", movie_name),
            )
        else:
            title = movie.get(
                "title",
                movie.get("original_title", movie_name),
            )

        title = clean_title(title)

        release_date = movie.get(
            "release_date",
            "",
        )

        year = release_date[:4]

        if year:
            filename = (
                f"{title} ({year})"
                f"{source.suffix.lower()}"
            )
        else:
            filename = (
                f"{title}"
                f"{source.suffix.lower()}"
            )

        destination = source.with_name(filename)

        return self._build_operation(
            source,
            destination,
        )

    def _best_match(self, query, results):
        if not results:
            return None

        best = None
        best_score = -1

        for result in results[:10]:
            candidates = [
                result.get("name", ""),
                result.get("original_name", ""),
                result.get("title", ""),
                result.get("original_title", ""),
            ]

            candidates = [
                candidate
                for candidate in candidates
                if candidate
            ]

            if not candidates:
                continue

            score = max(
                similarity(query, candidate)
                for candidate in candidates
            )

            if score > best_score:
                best_score = score
                best = result

        return best

    def _build_operation(
        self,
        source: Path,
        destination: Path,
    ) -> RenameOperation:

        subtitle_source = find_subtitle(source)

        if destination == source:
            return RenameOperation(
                source=source,
                destination=destination,
                subtitle_source=subtitle_source,
                status="unchanged",
                message="Arquivo já está com o nome proposto.",
            )

        subtitle_destination = None

        if subtitle_source:
            subtitle_destination = destination.with_suffix(
                subtitle_source.suffix
            )

        if destination.exists():
            return RenameOperation(
                source=source,
                destination=destination,
                subtitle_source=subtitle_source,
                subtitle_destination=subtitle_destination,
                status="collision",
                message=f"Destino já existe: {destination.name}",
            )

        if (
            subtitle_destination
            and subtitle_destination.exists()
        ):
            return RenameOperation(
                source=source,
                destination=destination,
                subtitle_source=subtitle_source,
                subtitle_destination=subtitle_destination,
                status="collision",
                message=(
                    "Destino da legenda já existe: "
                    f"{subtitle_destination.name}"
                ),
            )

        return RenameOperation(
            source=source,
            destination=destination,
            subtitle_source=subtitle_source,
            subtitle_destination=subtitle_destination,
            status="ready",
        )
