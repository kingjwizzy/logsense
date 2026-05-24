# src/api/app.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.

    Returns a fully configured app ready to be served by uvicorn.
    Using a factory function (rather than a module-level app object)
    makes the app easier to test and configure.
    """
    app = FastAPI(
        title="LogSense",
        description="Intelligent log analytics engine with AI-powered analysis.",
        version="1.0.0",
    )

    # Register route groups
    from src.api.routes import logs, health
    app.include_router(logs.router)
    app.include_router(health.router)

    return app


# Module-level app instance used by uvicorn
app = create_app()