"""
recommender.py

Responsibilities (per the task division report):
  - Keep genre names consistent / normalise them
  - Match movies against a user's favourite genres
  - Score and rank matches (more matching genres = higher rank)
  - Expose recommend_movies() as the single function Janindu's
    /recommendations endpoint calls

This module is framework-agnostic on purpose: it returns plain
Python dicts, never a FastAPI/Pydantic object, so it can be tested
and reused independently of the API layer.
"""

import json
from pathlib import Path

# Default location of the movie catalogue, relative to the project root.
DEFAULT_CATALOGUE_PATH = Path("app/data/movies.json")


class InvalidGenreInput(ValueError):
    """Raised when favorite_genres is missing, empty, or malformed.

    router should catch this and turn it into the agreed
    validation-error response.
    """
    pass


def normalize_genre(genre: str) -> str:
    """Lowercase + strip whitespace so 'Sci-Fi', ' sci-fi ', and 'SCI-FI'
    are all treated as the same genre.
    """
    if not isinstance(genre, str):
        raise InvalidGenreInput(f"Genre must be a string, got {type(genre).__name__}")
    return genre.strip().lower()


def load_movies(path: Path = DEFAULT_CATALOGUE_PATH) -> list[dict]:
    """Load the movie catalogue from disk.

    Kept separate from recommend_movies() so tests can pass in an
    in-memory list instead of touching the filesystem.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_favorite_genres(favorite_genres) -> set[str]:
    """Validate and normalise the incoming genre list.

    Returns a de-duplicated set of normalised genres.
    Raises InvalidGenreInput on missing/empty/invalid input.
    """
    if favorite_genres is None or not isinstance(favorite_genres, list):
        raise InvalidGenreInput("favorite_genres must be a non-empty list")

    if len(favorite_genres) == 0:
        raise InvalidGenreInput("favorite_genres must not be empty")

    normalized = {normalize_genre(g) for g in favorite_genres if str(g).strip() != ""}

    if not normalized:
        raise InvalidGenreInput("favorite_genres must contain at least one valid genre")

    return normalized


def recommend_movies(favorite_genres: list[str], movies: list[dict] | None = None) -> list[dict]:
    """Return movies matching the user's favourite genres, ranked by
    how many of the requested genres each movie matches.

    Args:
        favorite_genres: list of genre strings from the request,
            e.g. ["Action", "Sci-Fi"]
        movies: optional pre-loaded catalogue (mainly for tests).
            If omitted, loads from DEFAULT_CATALOGUE_PATH.

    Returns:
        A list of {"title": ..., "genres": ...} dicts only (no
        release_year, cast, description, etc.), ordered by number of
        matching genres (descending), with no duplicate titles. Empty
        list if nothing matches.

    Raises:
        InvalidGenreInput: if favorite_genres is missing, empty,
            or contains no usable values. Janindu's router converts
            this into the agreed validation-error response.
    """
    normalized_favs = _validate_favorite_genres(favorite_genres)

    if movies is None:
        movies = load_movies()

    scored = []
    for movie in movies:
        movie_genres = {normalize_genre(g) for g in movie["genres"]}
        match_count = len(normalized_favs & movie_genres)
        if match_count > 0:
            scored.append((match_count, movie))

    # Highest match count first. Ties keep catalogue order (stable sort).
    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = []
    seen_titles = set()
    for _, movie in scored:
        if movie["title"] in seen_titles:
            continue
        seen_titles.add(movie["title"])
        # Only expose title + genres, not the full catalogue record.
        results.append({"title": movie["title"], "genres": movie["genres"]})

    return results