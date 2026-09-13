# Movie_Recommendations
Using this simple application you can get your movie recommendation according to your vibe.

## Project structure

```
app/
  main.py                  # FastAPI application
  routers/recommendations.py  # POST /recommendations route
  schemas/recommendation.py   # Pydantic request/response models
  services/recommender.py     # Added by Kavin during integration
tests/
  test_api.py              # Endpoint tests (recommender is mocked)
```

## Installation

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Running the API

From the repository root:

```bash
uvicorn app.main:app --reload
```

The API is served at http://127.0.0.1:8000.

## Interactive docs

Open http://127.0.0.1:8000/docs for the Swagger UI. Expand **POST /recommendations**, click **Try it out**, edit the request body and click **Execute**. ReDoc is available at http://127.0.0.1:8000/redoc.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"favorite_genres": ["Action", "Sci-Fi"]}'
```

Response (`200 OK`):

```json
{
  "recommendations": [
    {
      "title": "Example Movie",
      "genre": "Action, Sci-Fi"
    }
  ]
}
```

If nothing matches, the response is `{"recommendations": []}`.

`favorite_genres` must be present, be a non-empty list, and contain only non-empty strings. Otherwise the API returns `422 Unprocessable Entity`.

The recommendation implementation is owned by Kavin and is intentionally not included in this feature branch. During integration, the API expects `app.services.recommender.recommend_movies(favorite_genres)`. Until that service is available, a valid request returns `503 Service Unavailable`; the endpoint contract is tested with a dependency override.

## Chatbot contract draft

> **Draft — not yet an endpoint.** These schemas live in `app/schemas/chatbot.py`. No chatbot route, AI extraction or TMDB integration exists yet.
>
> **`MovieClues` must be confirmed with Kavin before AI or TMDB integration begins.** It is the hand-off between the AI extraction service and the TMDB service.

Chatbot request (`ChatbotRequest`). `message` is required, must be a string, is trimmed, and cannot be blank:

```json
{
  "message": "A movie set in space where a father leaves his daughter for a mission."
}
```

Structured clues (`MovieClues`). All three fields are required and no others are allowed, so incomplete or malformed AI output is rejected before TMDB is called. `possible_title` must be present as a non-empty string or `null`. `genres` and `keywords` must be present as lists of non-empty strings, and may be empty (`[]`):

```json
{
  "possible_title": null,
  "genres": ["Sci-Fi", "Drama"],
  "keywords": ["space", "father", "daughter", "time dilation"]
}
```

Chatbot response (`ChatbotResponse` containing `MovieMatch` items). `poster_url` and `rating` may be `null`, `confidence` is between 0.0 and 1.0, and `best_match` is `null` when nothing matches. `alternatives` is always a list:

```json
{
  "best_match": {
    "title": "Interstellar",
    "overview": "...",
    "poster_url": "https://image.tmdb.org/example.jpg",
    "rating": 8.5,
    "confidence": 0.93
  },
  "alternatives": []
}
```

No-match response:

```json
{
  "best_match": null,
  "alternatives": []
}
```

## Running tests

From the repository root:

```bash
python -m pytest
```
