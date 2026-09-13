from collections.abc import Callable
from importlib import import_module
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

router = APIRouter(tags=["recommendations"])

RecommendMovies = Callable[[list[str]], list[dict[str, str]]]


def get_recommender() -> RecommendMovies:
    """Load Kavin's recommendation service when it is available."""
    try:
        recommender_module = import_module("app.services.recommender")
    except ModuleNotFoundError as exc:
        if exc.name not in {"app.services", "app.services.recommender"}:
            raise
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not available yet.",
        ) from exc

    return cast(RecommendMovies, recommender_module.recommend_movies)


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
    recommender: RecommendMovies = Depends(get_recommender),
) -> RecommendationResponse:
    movies = recommender(request.favorite_genres) or []
    return RecommendationResponse(recommendations=movies)
