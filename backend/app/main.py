import hmac
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.api.routes import downloads, media, settings, system, videos, ws
from app.core.config import Config, get_config
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.core.security import origin_allowed
from app.db.engine import init_db, make_engine, make_sessionmaker
from app.db.repos import DownloadRepo, SettingsRepo
from app.integrations.ytdlp import Binaries
from app.services.download_manager import DownloadManager
from app.services.events import EventBus
from app.services.extractor import Extractor
from app.services.runner import Runner
from app.services.storage import is_within

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(config: Config | None = None) -> FastAPI:
    config = config or get_config()
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config.ensure_dirs()
        setup_logging(config)
        engine = make_engine(config)
        await init_db(engine)
        sessions = make_sessionmaker(engine)
        repo = DownloadRepo(sessions)
        settings_repo = SettingsRepo(sessions)
        binaries = Binaries(config)
        await binaries.probe()
        extractor = Extractor(
            binaries.ytdlp or config.ytdlp_path or "yt-dlp", config.thumbnails_dir
        )
        runner = Runner(binaries.ytdlp or "yt-dlp", binaries.ffmpeg)
        events = EventBus()
        manager = DownloadManager(config, repo, settings_repo, extractor, runner, events)

        app.state.config = config
        app.state.repo = repo
        app.state.settings_repo = settings_repo
        app.state.binaries = binaries
        app.state.extractor = extractor
        app.state.events = events
        app.state.manager = manager
        await manager.start()
        try:
            yield
        finally:
            await manager.stop()
            await engine.dispose()

    app = FastAPI(title="Tube", version="1.0.0", lifespan=lifespan)
    app.state.token = token
    app.state.config = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.dev_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.host_list)

    @app.middleware("http")
    async def token_guard(request: Request, call_next):
        if (
            request.method in MUTATING_METHODS
            and request.url.path.startswith("/api")
            and not hmac.compare_digest(
                request.headers.get("x-vid-dwn-token", ""), token
            )
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Missing or invalid application token",
                        "details": {},
                    }
                },
            )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(videos.router)
    app.include_router(downloads.router)
    app.include_router(settings.router)
    app.include_router(system.router)
    app.include_router(media.router)
    app.include_router(ws.router)

    @app.get("/api/session")
    async def session(request: Request) -> dict:
        if not origin_allowed(
            request.headers.get("origin"), request.headers.get("host", ""), config
        ):
            raise AppError("FORBIDDEN_ORIGIN", "Origin is not allowed", 403)
        return {"token": token}

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api/"):
            raise AppError("NOT_FOUND", "Not found", 404)
        dist = config.frontend_dist
        if full_path:
            candidate = (dist / full_path).resolve()
            if is_within(candidate, dist) and candidate.is_file():
                return FileResponse(candidate)
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse(
                "<h1>Tube</h1><p>Frontend is not built yet. Run <code>make build</code>.</p>",
                status_code=200,
            )
        html = index.read_text().replace("__VID_DWN_TOKEN__", token)
        return HTMLResponse(html)

    return app


app = create_app()
