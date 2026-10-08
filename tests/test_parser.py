from media_renamed.core.parser import (
    extract_episode,
    extract_series_name,
    extract_movie_name,
    detect_media_type,
)
from media_renamed.core.models import MediaType
from pathlib import Path


def test_episode_sxxexx():
    assert extract_episode("Series.S03E01.mkv") == (3, 1)


def test_episode_nxnn():
    assert extract_episode("Series.3x01.mkv") == (3, 1)


def test_episode_none():
    assert extract_episode("Movie.2024.mkv") is None


def test_series_name():
    result = extract_series_name(
        "Star.Trek.Strange.New.Worlds.S03E01.mkv"
    )
    assert result == "Star Trek Strange New Worlds"


def test_movie_name_limpo():
    name = extract_movie_name(
        "Dune.Part.Two.2024.1080p.BluRay.x265.mkv"
    )
    assert "Dune" in name
    assert "1080p" not in name
    assert "BluRay" not in name
    assert "x265" not in name


def test_detect_tv():
    assert detect_media_type(Path("Show.S01E01.mkv")) == MediaType.TV


def test_detect_movie():
    assert detect_media_type(Path("Movie.2024.mkv")) == MediaType.MOVIE


def test_detect_audio():
    assert detect_media_type(Path("song.mp3")) == MediaType.MUSIC
