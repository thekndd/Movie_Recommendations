"""
test_services.py
Owner: Kavin

Covers the test cases assigned to Kavin in the acceptance plan:
  - Two favourite genres -> matches ranked with more genre overlap first
  - Lowercase input matches
  - Unknown genre -> empty list
  - Duplicate input genres -> no duplicate movies
    - Result records only contain title + genre
  - (Empty list / missing field validation is Janindu's endpoint-level test,
    but we test that recommend_movies() raises correctly here too.)

Run with: pytest tests/test_services.py
"""

import pytest
from app.services.recommender import recommend_movies, normalize_genre, InvalidGenreInput

SAMPLE_MOVIES = [
    {"title": "Interstellar", "genres": ["Sci-Fi", "Drama"]},
    {"title": "The Matrix", "genres": ["Action", "Sci-Fi"]},
    {"title": "Mad Max: Fury Road", "genres": ["Action", "Adventure"]},
    {"title": "Whiplash", "genres": ["Drama"]},
]


def test_two_genres_ranks_more_matches_first():
    result = recommend_movies(["Action", "Sci-Fi"], movies=SAMPLE_MOVIES)
    titles = [m["title"] for m in result]
    # The Matrix matches both genres, so it should rank above single-genre matches.
    assert titles[0] == "The Matrix"
    assert "Interstellar" in titles
    assert "Mad Max: Fury Road" in titles
    assert "Whiplash" not in titles  # only Drama, no overlap


def test_lowercase_input_matches():
    result = recommend_movies(["sci-fi"], movies=SAMPLE_MOVIES)
    titles = [m["title"] for m in result]
    assert "Interstellar" in titles
    assert "The Matrix" in titles


def test_unknown_genre_returns_empty_list():
    result = recommend_movies(["Unknown"], movies=SAMPLE_MOVIES)
    assert result == []


def test_duplicate_input_genres_no_duplicate_movies():
    result = recommend_movies(["Action", "action", "ACTION"], movies=SAMPLE_MOVIES)
    titles = [m["title"] for m in result]
    assert len(titles) == len(set(titles))  # no duplicates
    assert "The Matrix" in titles


def test_empty_list_raises():
    with pytest.raises(InvalidGenreInput):
        recommend_movies([], movies=SAMPLE_MOVIES)


def test_missing_field_raises():
    with pytest.raises(InvalidGenreInput):
        recommend_movies(None, movies=SAMPLE_MOVIES)


def test_normalize_genre_strips_and_lowercases():
    assert normalize_genre("  Sci-Fi ") == "sci-fi"


def test_returns_only_title_and_genre():
    movies_with_extra_fields = [
        {
            "title": "The Matrix",
            "release_year": 1999,
            "genres": ["Action", "Sci-Fi"],
            "cast": ["Keanu Reeves"],
            "description": "A hacker discovers the truth.",
        },
    ]
    result = recommend_movies(["Action"], movies=movies_with_extra_fields)
    assert result[0] == {"title": "The Matrix", "genre": "Action, Sci-Fi"}
    assert set(result[0].keys()) == {"title", "genre"}