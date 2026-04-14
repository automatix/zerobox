"""FastAPI app factory."""

from fastapi import FastAPI

from zerobox.config import AppConfig, load_config


def create_app() -> FastAPI:
    config = load_config()
    app = FastAPI(title="Zerobox", version="0.1.0")
    app.state.config = config
    app.state.proposals: dict[str, dict] = {}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/config")
    async def get_config() -> dict:
        return config.model_dump(mode="json")

    # Include routers
    from zerobox.api.routes import audit, pipeline, proposals, rules

    app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
    app.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
    app.include_router(rules.router, prefix="/rules", tags=["rules"])
    app.include_router(audit.router, prefix="/audit", tags=["audit"])

    return app
