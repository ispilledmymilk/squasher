# backend/api/main.py

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from data.metrics_store import MetricsStore
from utils.config import config
from utils.logger import setup_logger

from .routes import analysis, metrics
from .websocket import ConnectionManager

logger = setup_logger(__name__)

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from utils.progress_bus import configure, reset

    config.ensure_directories()
    logger.info(
        "CodeDecay QA API starting env=%s host=%s port=%s",
        config.ENV,
        config.BACKEND_HOST,
        config.BACKEND_PORT,
    )
    if config.IS_PRODUCTION and config.API_SECRET_KEY:
        logger.info("API authentication enabled (API_SECRET_KEY set)")

    progress_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    configure(asyncio.get_running_loop(), progress_queue)

    async def drain_progress() -> None:
        while True:
            event = await progress_queue.get()
            try:
                await manager.broadcast(json.dumps(event))
            except Exception:
                logger.exception("WebSocket progress broadcast failed")

    drain_task = asyncio.create_task(drain_progress())
    try:
        yield
    finally:
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass
        reset()
        logger.info("CodeDecay QA API shutting down.")


app = FastAPI(
    title="CodeDecay QA API",
    description="Production QA API: code quality, pre-commit checks, and technical-debt signals.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: production should list explicit origins; dev allows * if unset
_cors = config.CORS_ORIGINS
if config.IS_PRODUCTION and not _cors:
    _cors_allow = []
elif not _cors:
    _cors_allow = ["*"]
else:
    _cors_allow = _cors

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow,
    allow_credentials=bool(_cors_allow and _cors_allow != ["*"]),
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(
    analysis.router, prefix="/api/analysis", tags=["Analysis"]
)
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error path=%s", request.url.path)
    detail = (
        "Internal server error"
        if config.IS_PRODUCTION and not config.EXPOSE_ERROR_DETAILS
        else str(exc)
    )
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "codedecay-qa",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Liveness: process is up."""
    return {
        "status": "healthy",
        "service": "codedecay-qa",
    }


@app.get("/health/ready")
async def health_ready():
    """Readiness: dependencies reachable (SQLite metrics DB)."""
    try:
        from sqlalchemy import text

        store = MetricsStore()
        with store.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        logger.error("Readiness check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error"},
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time analysis progress: JSON events with type \"analysis_progress\".
    Client may send {\"type\":\"ping\"} for {\"type\":\"pong\"}.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
                if msg.get("type") == "subscribe":
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "subscribed",
                                "channel": msg.get("channel", "analysis"),
                            }
                        )
                    )
                    continue
            except json.JSONDecodeError:
                pass
            await websocket.send_text(
                json.dumps({"type": "echo", "data": data})
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.BACKEND_HOST,
        port=config.BACKEND_PORT,
        reload=not config.IS_PRODUCTION,
        log_level=config.LOG_LEVEL.lower(),
    )
