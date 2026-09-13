from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

NonEmptyText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


class ChatbotRequest(BaseModel):
    message: NonEmptyText = Field(
        ...,
        description="Free-text description of the movie the user is looking for.",
        examples=["A movie set in space where a father leaves his daughter for a mission."],
    )


class MovieClues(BaseModel):
    """Draft interface between the AI extraction service and the TMDB service."""

    model_config = ConfigDict(extra="forbid")

    # All fields are required (no defaults) so incomplete AI output is rejected.
    possible_title: NonEmptyText | None
    genres: list[NonEmptyText]
    keywords: list[NonEmptyText]


class MovieMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonEmptyText
    overview: Annotated[str, Field(strict=True)]
    poster_url: HttpUrl | None = None
    rating: Annotated[float, Field(strict=True)] | None = None
    confidence: Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class ChatbotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    best_match: MovieMatch | None = None
    alternatives: list[MovieMatch] = Field(default_factory=list)
