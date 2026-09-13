from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.recommendations import get_recommender

client = TestClient(app)


@pytest.fixture
def mock_recommender() -> Mock:
    recommender = Mock()
    app.dependency_overrides[get_recommender] = lambda: recommender
    yield recommender
    app.dependency_overrides.clear()


def test_valid_single_genre_request(mock_recommender: Mock) -> None:
    movies = [{"title": "Mad Max: Fury Road", "genre": "Action"}]
    mock_recommender.return_value = movies

    response = client.post("/recommendations", json={"favorite_genres": ["Action"]})

    assert response.status_code == 200
    assert response.json() == {"recommendations": movies}
    mock_recommender.assert_called_once_with(["Action"])


def test_multiple_genres_request(mock_recommender: Mock) -> None:
    movies = [
        {"title": "The Matrix", "genre": "Action, Sci-Fi"},
        {"title": "Inception", "genre": "Action, Sci-Fi"},
    ]
    mock_recommender.return_value = movies

    response = client.post(
        "/recommendations", json={"favorite_genres": ["Action", "Sci-Fi"]}
    )

    assert response.status_code == 200
    assert response.json() == {"recommendations": movies}
    mock_recommender.assert_called_once_with(["Action", "Sci-Fi"])


def test_empty_genre_list_is_rejected(mock_recommender: Mock) -> None:
    response = client.post("/recommendations", json={"favorite_genres": []})

    assert response.status_code == 422
    mock_recommender.assert_not_called()


@pytest.mark.parametrize("body", [{}, {"genres": ["Action"]}])
def test_missing_favorite_genres_is_rejected(body: dict, mock_recommender: Mock) -> None:
    response = client.post("/recommendations", json=body)

    assert response.status_code == 422
    mock_recommender.assert_not_called()


@pytest.mark.parametrize(
    "favorite_genres",
    ["Action", ["Action", ""], ["   "], ["Action", 123], [None], [["Action"]]],
)
def test_invalid_genre_values_are_rejected(
    favorite_genres: object, mock_recommender: Mock
) -> None:
    response = client.post(
        "/recommendations", json={"favorite_genres": favorite_genres}
    )

    assert response.status_code == 422
    mock_recommender.assert_not_called()


def test_service_returning_no_matches(mock_recommender: Mock) -> None:
    mock_recommender.return_value = []

    response = client.post("/recommendations", json={"favorite_genres": ["Western"]})

    assert response.status_code == 200
    assert response.json() == {"recommendations": []}
