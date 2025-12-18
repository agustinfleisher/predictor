"""
FastAPI app wrapping the stockpredictor pipeline with auth and job endpoints.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .config import get_settings
from .jobs import router as jobs_router
from .storage import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    init_db(settings)
    app = FastAPI(title="stockpredictor API", version="0.1.0")

    # Allow local frontends (file://, localhost) to call the API during development.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(jobs_router)
    return app


app = create_app()
