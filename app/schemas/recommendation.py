from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

NonEmptyGenre = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]


class RecommendationRequest(BaseModel):
    favorite_genres: list[NonEmptyGenre] = Field(
        ...,
        min_length=1,
        examples=[["Action", "Sci-Fi"]],
        description="One or more favourite genres.",
    )


class Movie(BaseModel):
    title: str
    genre: str


class RecommendationResponse(BaseModel):
    recommendations: list[Movie] = Field(default_factory=list)
