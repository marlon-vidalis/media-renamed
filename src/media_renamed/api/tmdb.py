import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def find_env_file() -> Path:
    current = Path(__file__).resolve()

    for directory in current.parents:
        env_file = directory / ".env"

        if env_file.exists():
            return env_file

    return current.parents[3] / ".env"


ENV_FILE = find_env_file()
load_dotenv(ENV_FILE)


def normalize_language(language: str) -> str:
    mapping = {
        "en": "en-US",
        "pt": "pt-BR",
        "es": "es-ES",
        "fr": "fr-FR",
        "de": "de-DE",
        "it": "it-IT",
        "ja": "ja-JP",
        "ko": "ko-KR",
    }

    return mapping.get(language, language)


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self):
        token = os.getenv("TMDB_TOKEN")

        if not token:
            raise RuntimeError(
                f"TMDB_TOKEN não encontrado em {ENV_FILE}"
            )

        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        })

    def get(self, endpoint, params=None):
        response = self.session.get(
            f"{self.BASE_URL}{endpoint}",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def search_tv(self, query, language="pt-BR"):
        return self.get(
            "/search/tv",
            {
                "query": query,
                "language": language,
            },
        )

    def search_movie(self, query, language="pt-BR"):
        return self.get(
            "/search/movie",
            {
                "query": query,
                "language": language,
            },
        )

    def get_tv(self, series_id, language="pt-BR"):
        return self.get(
            f"/tv/{series_id}",
            {
                "language": language,
            },
        )

    def get_episode(
        self,
        series_id,
        season,
        episode,
        language="pt-BR",
    ):
        return self.get(
            f"/tv/{series_id}/season/{season}/episode/{episode}",
            {
                "language": language,
            },
        )

    def get_movie(self, movie_id, language="pt-BR"):
        return self.get(
            f"/movie/{movie_id}",
            {
                "language": language,
            },
        )
