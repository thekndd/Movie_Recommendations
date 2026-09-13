from fastapi import FastAPI

from app.routers import recommendations

app = FastAPI(
    title="Movie Recommendation API",
    description="Get movie recommendations based on your favourite genres.",
    version="0.1.0",
)

app.include_router(recommendations.router)
