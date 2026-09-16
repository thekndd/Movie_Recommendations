import pytest
from pydantic import ValidationError

from app.schemas import ChatbotRequest, ChatbotResponse, MovieClues, MovieMatch

VALID_MATCH = {
    "title": "Interstellar",
    "overview": "Explorers travel through a wormhole in space.",
    "poster_url": "https://image.tmdb.org/example.jpg",
    "rating": 8.5,
    "confidence": 0.93,
}


# ChatbotRequest


def test_valid_chatbot_message_is_trimmed() -> None:
    request = ChatbotRequest.model_validate({"message": "  A movie set in space.  "})

    assert request.message == "A movie set in space."


def test_missing_message_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatbotRequest.model_validate({})


@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_empty_or_whitespace_message_is_rejected(message: str) -> None:
    with pytest.raises(ValidationError):
        ChatbotRequest.model_validate({"message": message})


@pytest.mark.parametrize("message", [123, 1.5, True, None, ["space"], {"text": "space"}])
def test_non_string_message_is_rejected(message: object) -> None:
    with pytest.raises(ValidationError):
        ChatbotRequest.model_validate({"message": message})


# MovieClues


def test_valid_structured_clues() -> None:
    clues = MovieClues.model_validate(
        {
            "possible_title": " Interstellar ",
            "genres": ["Sci-Fi", " Drama "],
            "keywords": ["space", "father", "daughter", "time dilation"],
        }
    )

    assert clues.possible_title == "Interstellar"
    assert clues.genres == ["Sci-Fi", "Drama"]
    assert clues.keywords == ["space", "father", "daughter", "time dilation"]


def test_possible_title_can_be_null() -> None:
    clues = MovieClues.model_validate(
        {"possible_title": None, "genres": ["Sci-Fi"], "keywords": ["space"]}
    )

    assert clues.possible_title is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"possible_title": ""},
        {"possible_title": "   "},
        {"genres": ["Sci-Fi", ""]},
        {"keywords": ["   "]},
    ],
)
def test_blank_clue_values_are_rejected(overrides: dict) -> None:
    data = {"possible_title": None, "genres": ["Sci-Fi"], "keywords": ["space"]} | overrides

    with pytest.raises(ValidationError):
        MovieClues.model_validate(data)


@pytest.mark.parametrize("field", ["genres", "keywords"])
@pytest.mark.parametrize("value", [[123], [None], [["space"]], [{"a": "b"}], "space"])
def test_invalid_clue_list_values_are_rejected(field: str, value: object) -> None:
    data = {"possible_title": None, "genres": ["Sci-Fi"], "keywords": ["space"]}
    data[field] = value

    with pytest.raises(ValidationError):
        MovieClues.model_validate(data)


@pytest.mark.parametrize("title", [42, ["Interstellar"]])
def test_non_string_possible_title_is_rejected(title: object) -> None:
    with pytest.raises(ValidationError):
        MovieClues.model_validate({"possible_title": title, "genres": [], "keywords": []})


def test_empty_clues_object_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MovieClues.model_validate({})


@pytest.mark.parametrize("missing", ["possible_title", "genres", "keywords"])
def test_missing_clue_field_is_rejected(missing: str) -> None:
    data = {"possible_title": None, "genres": [], "keywords": []}
    del data[missing]

    with pytest.raises(ValidationError) as exc_info:
        MovieClues.model_validate(data)

    errors = exc_info.value.errors()
    assert [(e["type"], e["loc"]) for e in errors] == [("missing", (missing,))]


def test_null_title_and_empty_clue_lists_are_accepted() -> None:
    clues = MovieClues.model_validate({"possible_title": None, "genres": [], "keywords": []})

    assert clues.model_dump() == {"possible_title": None, "genres": [], "keywords": []}


def test_unexpected_clue_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        MovieClues.model_validate(
            {"possible_title": None, "genres": [], "keywords": [], "year": 2014}
        )


# MovieMatch / ChatbotResponse


def test_valid_chatbot_response() -> None:
    response = ChatbotResponse.model_validate(
        {"best_match": VALID_MATCH, "alternatives": [VALID_MATCH | {"confidence": 0.4}]}
    )

    assert response.best_match is not None
    assert response.best_match.title == "Interstellar"
    assert str(response.best_match.poster_url) == VALID_MATCH["poster_url"]
    assert len(response.alternatives) == 1


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_out_of_range_is_rejected(confidence: float) -> None:
    with pytest.raises(ValidationError):
        MovieMatch.model_validate(VALID_MATCH | {"confidence": confidence})


@pytest.mark.parametrize("confidence", [0, 0.0, 1, 1.0])
def test_confidence_boundaries_are_accepted(confidence: float) -> None:
    assert MovieMatch.model_validate(VALID_MATCH | {"confidence": confidence})


def test_null_poster_url_and_rating_are_accepted() -> None:
    match = MovieMatch.model_validate(VALID_MATCH | {"poster_url": None, "rating": None})

    assert match.poster_url is None
    assert match.rating is None


@pytest.mark.parametrize(
    "overrides",
    [{"poster_url": "not-a-url"}, {"title": "  "}, {"rating": "8.5"}, {"confidence": "0.9"}],
)
def test_invalid_movie_match_values_are_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        MovieMatch.model_validate(VALID_MATCH | overrides)


def test_null_best_match_and_empty_alternatives() -> None:
    response = ChatbotResponse.model_validate({"best_match": None})

    assert response.best_match is None
    assert response.alternatives == []
    assert response.model_dump() == {"best_match": None, "alternatives": []}


def test_unexpected_response_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatbotResponse.model_validate({"best_match": None, "alternatives": [], "debug": True})
