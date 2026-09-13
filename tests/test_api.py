from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Patch the name as imported by the router so the real recommender is never used.
RECOMMENDER_PATH = "app.routers.recommendations.recommend_movies"


def test_valid_single_genre_request() -> None:
    movies = [{"title": "Mad Max: Fury Road", "genre": "Action"}]
    with patch(RECOMMENDER_PATH, return_value=movies) as mock_recommend:
        response = client.post("/recommendations", json={"favorite_genres": ["Action"]})

    assert response.status_code == 200
    assert response.json() == {"recommendations": movies}
    mock_recommend.assert_called_once_with(["Action"])


def test_multiple_genres_request() -> None:
    movies = [
        {"title": "The Matrix", "genre": "Action, Sci-Fi"},
        {"title": "Inception", "genre": "Action, Sci-Fi"},
    ]
    with patch(RECOMMENDER_PATH, return_value=movies) as mock_recommend:
        response = client.post(
            "/recommendations", json={"favorite_genres": ["Action", "Sci-Fi"]}
        )

    assert response.status_code == 200
    assert response.json() == {"recommendations": movies}
    mock_recommend.assert_called_once_with(["Action", "Sci-Fi"])


def test_empty_genre_list_is_rejected() -> None:
    with patch(RECOMMENDER_PATH) as mock_recommend:
        response = client.post("/recommendations", json={"favorite_genres": []})

    assert response.status_code == 422
    mock_recommend.assert_not_called()


@pytest.mark.parametrize("body", [{}, {"genres": ["Action"]}])
def test_missing_favorite_genres_is_rejected(body: dict) -> None:
    with patch(RECOMMENDER_PATH) as mock_recommend:
        response = client.post("/recommendations", json=body)

    assert response.status_code == 422
    mock_recommend.assert_not_called()


@pytest.mark.parametrize(
    "favorite_genres",
    ["Action", ["Action", ""], ["   "], ["Action", 123], [None], [["Action"]]],
)
def test_invalid_genre_values_are_rejected(favorite_genres: object) -> None:
    with patch(RECOMMENDER_PATH) as mock_recommend:
        response = client.post(
            "/recommendations", json={"favorite_genres": favorite_genres}
        )

    assert response.status_code == 422
    mock_recommend.assert_not_called()


def test_service_returning_no_matches() -> None:
    with patch(RECOMMENDER_PATH, return_value=[]):
        response = client.post("/recommendations", json={"favorite_genres": ["Western"]})

    assert response.status_code == 200
    assert response.json() == {"recommendations": []}
