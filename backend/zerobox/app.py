"""FastAPI app factory."""

from fastapi import FastAPI

from zerobox.config import AppConfig, load_config


def create_app() -> FastAPI:
    config = load_config()
    app = FastAPI(title="Zerobox", version="0.1.0")
    app.state.config = config

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/config")
    async def get_config() -> dict:
        return config.model_dump(mode="json")

    return app
