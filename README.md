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

## Running tests

From the repository root:

```bash
python -m pytest
```
