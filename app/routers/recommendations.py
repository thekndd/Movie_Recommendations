from fastapi import APIRouter

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommender import recommend_movies

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    movies = recommend_movies(request.favorite_genres) or []
    return RecommendationResponse(recommendations=movies)
