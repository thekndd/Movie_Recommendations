import json
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import groq
import httpx
import pytest

from app.schemas.chatbot import MovieClues
from app.services import ai_extractor
from app.services.ai_extractor import (
    DEFAULT_MODEL,
    MOVIE_CLUES_JSON_SCHEMA,
    AIConfigurationError,
    AIExtractionError,
    AIInputError,
    AIResponseError,
    AIServiceError,
    extract_movie_clues,
)

FAKE_API_KEY = "test-key-not-real-0123456789"
DESCRIPTION = "A movie set in space where a father leaves his daughter for a mission."
VALID_CLUES = {
    "possible_title": None,
    "genres": ["Sci-Fi", "Drama"],
    "keywords": ["space", "father", "daughter"],
}
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def make_response(content: object) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def json_response(data: object) -> SimpleNamespace:
    return make_response(json.dumps(data))


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ignore any local .env and start every test from a known environment."""
    monkeypatch.setattr(ai_extractor, "load_dotenv", lambda *args, **kwargs: False)
    for name in ("AI_API_KEY", "AI_MODEL", "REQUEST_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_API_KEY", FAKE_API_KEY)


@pytest.fixture
def groq_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[MagicMock]:
    """Replace the Groq class so no network call can happen."""
    client = MagicMock()
    client.chat.completions.create.return_value = json_response(VALID_CLUES)
    groq_class = MagicMock(return_value=client)
    monkeypatch.setattr(ai_extractor, "Groq", groq_class)
    client.groq_class = groq_class
    yield client


def create_kwargs(client: MagicMock) -> dict:
    client.chat.completions.create.assert_called_once()
    return client.chat.completions.create.call_args.kwargs


# Successful extraction


def test_valid_description_returns_movie_clues(groq_client: MagicMock) -> None:
    clues = extract_movie_clues(DESCRIPTION)

    assert isinstance(clues, MovieClues)
    assert clues.model_dump() == VALID_CLUES


def test_known_possible_title(groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(
        VALID_CLUES | {"possible_title": "Interstellar"}
    )

    assert extract_movie_clues("Interstellar").possible_title == "Interstellar"


def test_null_possible_title(groq_client: MagicMock) -> None:
    assert extract_movie_clues(DESCRIPTION).possible_title is None


def test_empty_genres_and_keywords(groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(
        {"possible_title": None, "genres": [], "keywords": []}
    )

    clues = extract_movie_clues("Something good")

    assert clues.genres == []
    assert clues.keywords == []


def test_whitespace_is_trimmed_in_input_and_output(groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(
        {"possible_title": " Interstellar ", "genres": [" Sci-Fi "], "keywords": [" space "]}
    )

    clues = extract_movie_clues(f"   {DESCRIPTION}\n")

    user_message = create_kwargs(groq_client)["messages"][1]
    assert user_message == {"role": "user", "content": DESCRIPTION}
    assert clues.model_dump() == {
        "possible_title": "Interstellar",
        "genres": ["Sci-Fi"],
        "keywords": ["space"],
    }


# Input validation


@pytest.mark.parametrize("message", [123, None, ["space"], {"message": "space"}, b"space"])
def test_non_string_input_is_rejected(message: object, groq_client: MagicMock) -> None:
    with pytest.raises(AIInputError):
        extract_movie_clues(message)  # type: ignore[arg-type]

    groq_client.groq_class.assert_not_called()


@pytest.mark.parametrize("message", ["", "   ", "\n\t "])
def test_empty_or_whitespace_input_is_rejected(message: str, groq_client: MagicMock) -> None:
    with pytest.raises(AIInputError):
        extract_movie_clues(message)

    groq_client.groq_class.assert_not_called()


# Configuration


def test_ai_model_env_is_passed_to_groq(
    monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    monkeypatch.setenv("AI_MODEL", "llama-3.3-70b-versatile")

    extract_movie_clues(DESCRIPTION)

    assert create_kwargs(groq_client)["model"] == "llama-3.3-70b-versatile"


def test_default_model_when_ai_model_missing(groq_client: MagicMock) -> None:
    extract_movie_clues(DESCRIPTION)

    assert create_kwargs(groq_client)["model"] == DEFAULT_MODEL == "openai/gpt-oss-20b"


def test_default_model_when_ai_model_blank(
    monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    monkeypatch.setenv("AI_MODEL", "   ")

    extract_movie_clues(DESCRIPTION)

    assert create_kwargs(groq_client)["model"] == DEFAULT_MODEL


def test_api_key_and_timeout_are_passed_to_client(
    monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    monkeypatch.setenv("REQUEST_TIMEOUT", "2.5")

    extract_movie_clues(DESCRIPTION)

    groq_client.groq_class.assert_called_once_with(api_key=FAKE_API_KEY, timeout=2.5)


@pytest.mark.parametrize("value", [None, "", "  "])
def test_default_timeout_when_missing_or_blank(
    value: str | None, monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    if value is not None:
        monkeypatch.setenv("REQUEST_TIMEOUT", value)

    extract_movie_clues(DESCRIPTION)

    groq_client.groq_class.assert_called_once_with(api_key=FAKE_API_KEY, timeout=10.0)


@pytest.mark.parametrize("value", ["abc", "10s", "nan", "inf", "0", "0.0", "-1", "-0.5"])
def test_invalid_timeout_is_rejected(
    value: str, monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    monkeypatch.setenv("REQUEST_TIMEOUT", value)

    with pytest.raises(AIConfigurationError):
        extract_movie_clues(DESCRIPTION)

    groq_client.groq_class.assert_not_called()


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_api_key_is_rejected_before_groq_call(
    value: str | None, monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    if value is None:
        monkeypatch.delenv("AI_API_KEY")
    else:
        monkeypatch.setenv("AI_API_KEY", value)

    with pytest.raises(AIConfigurationError, match="AI API key is not configured."):
        extract_movie_clues(DESCRIPTION)

    groq_client.groq_class.assert_not_called()
    groq_client.chat.completions.create.assert_not_called()


# Request shape


def test_system_and_user_messages(groq_client: MagicMock) -> None:
    extract_movie_clues(DESCRIPTION)

    system, user = create_kwargs(groq_client)["messages"]
    assert system == {"role": "system", "content": ai_extractor.SYSTEM_PROMPT}
    assert DESCRIPTION not in system["content"]
    assert user == {"role": "user", "content": DESCRIPTION}


def test_structured_output_response_format(groq_client: MagicMock) -> None:
    extract_movie_clues(DESCRIPTION)

    kwargs = create_kwargs(groq_client)
    response_format = kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["name"] == "movie_clues"
    assert response_format["json_schema"]["schema"] is MOVIE_CLUES_JSON_SCHEMA
    assert kwargs["temperature"] == 0
    assert kwargs["stream"] is False
    assert "tools" not in kwargs


def test_schema_requires_fields_and_forbids_extras() -> None:
    assert MOVIE_CLUES_JSON_SCHEMA["required"] == ["possible_title", "genres", "keywords"]
    assert MOVIE_CLUES_JSON_SCHEMA["additionalProperties"] is False
    assert set(MOVIE_CLUES_JSON_SCHEMA["properties"]) == {"possible_title", "genres", "keywords"}


# Invalid AI responses


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=None),
        SimpleNamespace(),
    ],
    ids=["empty-choices", "null-choices", "no-choices"],
)
def test_missing_choices_are_rejected(response: object, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = response

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


@pytest.mark.parametrize(
    "response",
    [
        make_response(None),
        SimpleNamespace(choices=[SimpleNamespace(message=None)]),
        SimpleNamespace(choices=[SimpleNamespace()]),
    ],
    ids=["null-content", "null-message", "no-message"],
)
def test_missing_content_is_rejected(response: object, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = response

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


@pytest.mark.parametrize("content", ["", "   "])
def test_empty_content_is_rejected(content: str, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = make_response(content)

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


@pytest.mark.parametrize(
    "content", ["not json", '{"possible_title": null,', "```json\n{}\n```"]
)
def test_invalid_json_is_rejected(content: str, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = make_response(content)

    with pytest.raises(AIResponseError) as exc_info:
        extract_movie_clues(DESCRIPTION)

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize("data", [[VALID_CLUES], "clues", 42, None])
def test_non_object_json_is_rejected(data: object, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(data)

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


@pytest.mark.parametrize("missing", ["possible_title", "genres", "keywords"])
def test_missing_clue_field_is_rejected(missing: str, groq_client: MagicMock) -> None:
    data = dict(VALID_CLUES)
    del data[missing]
    groq_client.chat.completions.create.return_value = json_response(data)

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


def test_extra_fields_are_rejected(groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(
        VALID_CLUES | {"confidence": 0.9}
    )

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


@pytest.mark.parametrize(
    "overrides",
    [
        {"possible_title": 42},
        {"possible_title": ["Interstellar"]},
        {"genres": "Sci-Fi"},
        {"genres": [1]},
        {"genres": [None]},
        {"keywords": [["space"]]},
        {"keywords": None},
    ],
)
def test_invalid_clue_field_types_are_rejected(overrides: dict, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(VALID_CLUES | overrides)

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


@pytest.mark.parametrize(
    "overrides",
    [
        {"possible_title": ""},
        {"possible_title": "   "},
        {"genres": ["Sci-Fi", ""]},
        {"genres": ["  "]},
        {"keywords": ["space", ""]},
        {"keywords": ["\t"]},
    ],
    ids=["title-empty", "title-blank", "genre-empty", "genre-blank", "kw-empty", "kw-blank"],
)
def test_blank_clue_values_are_rejected(overrides: dict, groq_client: MagicMock) -> None:
    groq_client.chat.completions.create.return_value = json_response(VALID_CLUES | overrides)

    with pytest.raises(AIResponseError):
        extract_movie_clues(DESCRIPTION)


# Groq failures


def _request() -> httpx.Request:
    return httpx.Request("POST", GROQ_URL)


def _status_error(cls: type[groq.APIStatusError], status_code: int) -> groq.APIStatusError:
    response = httpx.Response(status_code, request=_request())
    return cls(f"Error {status_code} for key {FAKE_API_KEY}", response=response, body=None)


ProviderErrorFactory = Callable[[], Exception]


@pytest.mark.parametrize(
    ("make_error", "expected_message"),
    [
        (lambda: groq.APITimeoutError(request=_request()), "AI request timed out."),
        (lambda: groq.APIConnectionError(request=_request()), "AI service is unavailable."),
        (
            lambda: _status_error(groq.AuthenticationError, 401),
            "AI service rejected the request.",
        ),
        (lambda: _status_error(groq.RateLimitError, 429), "AI service rate limit reached."),
        (lambda: _status_error(groq.BadRequestError, 400), "AI service rejected the request."),
        (lambda: _status_error(groq.InternalServerError, 500), "AI service is unavailable."),
        (lambda: _status_error(groq.APIStatusError, 503), "AI service is unavailable."),
    ],
    ids=["timeout", "connection", "auth", "rate-limit", "bad-request", "server", "status"],
)
def test_groq_errors_become_service_errors(
    make_error: ProviderErrorFactory, expected_message: str, groq_client: MagicMock
) -> None:
    provider_error = make_error()
    groq_client.chat.completions.create.side_effect = provider_error

    with pytest.raises(AIServiceError) as exc_info:
        extract_movie_clues(DESCRIPTION)

    assert str(exc_info.value) == expected_message
    assert exc_info.value.__cause__ is provider_error


# Secret handling


@pytest.mark.parametrize(
    "setup",
    ["timeout-config", "auth-error", "invalid-json", "validation-error"],
)
def test_application_errors_never_contain_api_key(
    setup: str, monkeypatch: pytest.MonkeyPatch, groq_client: MagicMock
) -> None:
    create = groq_client.chat.completions.create
    if setup == "timeout-config":
        monkeypatch.setenv("REQUEST_TIMEOUT", "bad")
    elif setup == "auth-error":
        create.side_effect = _status_error(groq.AuthenticationError, 401)
    elif setup == "invalid-json":
        create.return_value = make_response(f"not json {FAKE_API_KEY}")
    else:
        create.return_value = json_response(VALID_CLUES | {"possible_title": 1})

    with pytest.raises(AIExtractionError) as exc_info:
        extract_movie_clues(DESCRIPTION)

    assert FAKE_API_KEY not in str(exc_info.value)
    assert FAKE_API_KEY not in repr(exc_info.value)


def test_error_hierarchy() -> None:
    for error in (AIInputError, AIConfigurationError, AIServiceError, AIResponseError):
        assert issubclass(error, AIExtractionError)
