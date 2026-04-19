"""FastAPI app factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from zerobox.config import AppConfig, load_config

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "tauri://localhost",
    "http://tauri.localhost",
]


def create_app() -> FastAPI:
    config = load_config()
    app = FastAPI(title="zerobox", version="0.5.1")
    app.state.config = config
    app.state.proposals: dict[str, dict] = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Global exception handlers
    # ------------------------------------------------------------------

    @app.exception_handler(FileNotFoundError)
    async def not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # ------------------------------------------------------------------
    # Built-in routes
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/config")
    async def get_config() -> dict:
        # Read via the cached dependency so /setup/save's reload_config() is
        # visible here (the closure variable above is set once at startup).
        from zerobox.api.dependencies import get_config as _get_cached_config

        return _get_cached_config().model_dump(mode="json")

    # Include routers
    from zerobox.api.routes import audit, pipeline, proposals, rules, setup

    app.include_router(setup.router, prefix="/setup", tags=["setup"])
    app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
    app.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
    app.include_router(rules.router, prefix="/rules", tags=["rules"])
    app.include_router(audit.router, prefix="/audit", tags=["audit"])

    return app
