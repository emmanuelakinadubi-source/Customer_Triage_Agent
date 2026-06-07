from fastapi import FastAPI

from .api.routes import router as api_router
from .core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_title, version=settings.app_version)
    app.include_router(api_router)
    return app


app = create_app()
