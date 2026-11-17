"""Point d'entrée FastAPI. `create_app()` permet aux tests d'utiliser une base isolée."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from . import __version__, services
from .config import DEV_ADMIN_PASSWORD, DEV_SECRET, get_settings
from .database import make_engine
from .errors import register_handlers
from .models import Base
from .routers import accounts, admin, auth, transfers

STATIC_DIR = Path(__file__).parent / "static"

_CSP = "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    if settings.env == "production" and (settings.secret == DEV_SECRET or settings.admin_password == DEV_ADMIN_PASSWORD):
        raise RuntimeError("Production : définissez BANKSIM_SECRET et BANKSIM_ADMIN_PASSWORD.")

    engine = make_engine(database_url or settings.database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as db:
        services.bootstrap(db, settings)

    app = FastAPI(title="BankSim API", version=__version__,
                  description="Banque fictive à but pédagogique (projet de développement et de test assistés par IA).")
    app.state.SessionLocal = session_factory
    app.state.engine = engine
    register_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        elif not request.url.path.startswith(("/docs", "/redoc", "/openapi")):
            response.headers["Content-Security-Policy"] = _CSP
        return response

    for r in (auth.router, accounts.router, transfers.router, admin.router):
        app.include_router(r)

    @app.get("/api/health", tags=["Technique"])
    def health():
        return {"status": "ok", "version": __version__}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app
