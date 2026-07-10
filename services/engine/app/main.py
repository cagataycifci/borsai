"""FastAPI application factory and entrypoint.

Run in development with:
    uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload

In the packaged desktop app, the Electron main process spawns this engine and
supervises its lifecycle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai import AIService, build_ai_provider
from app.alerts import AlertMonitor, AlertService, ConnectionHub
from app.api.ai_routes import router as ai_router
from app.api.alert_routes import router as alert_router
from app.api.commentator_routes import router as commentator_router
from app.api.news_routes import router as news_router
from app.api.portfolio_routes import router as portfolio_router
from app.api.routes import router as api_router
from app.api.scheduler_routes import router as scheduler_router
from app.api.search_routes import router as search_router
from app.api.settings_routes import router as settings_router
from app.api.symbol_routes import router as symbol_router
from app.api.watchlist_routes import router as watchlist_router
from app.api.ws import ws_router
from app.commentator import CommentatorService
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.data.factory import build_market_data_service
from app.data.universe.service import SymbolUniverseService
from app.db.session import init_db
from app.news import NewsService
from app.portfolio import PortfolioService
from app.scheduler import JobContext, ReportService, SchedulerManager
from app.search import GlobalSearchService
from app.settings.service import SecretsService, SettingsService
from app.watchlists import WatchlistService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Construct long-lived services on startup; tidy up on shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting %s v%s", settings.app_name, __version__)
    logger.info("Data dir: %s", settings.data_dir)

    # Database + schema migrations.
    init_db()

    # Settings & secrets services.
    app.state.settings_service = SettingsService()
    app.state.secrets_service = SecretsService()

    # Symbol universe (seed on first run; non-blocking on network failure).
    app.state.symbol_universe = SymbolUniverseService()
    if settings.auto_seed:
        await app.state.symbol_universe.ensure_seeded()

    # Watchlists (seed a starter list on first run) + portfolio holdings.
    app.state.watchlist_service = WatchlistService()
    app.state.watchlist_service.ensure_default()
    app.state.portfolio_service = PortfolioService()

    # News aggregation (refresh is on-demand — no blocking network at startup).
    app.state.news_service = NewsService()

    # Compose the data layer from the configured provider order + secrets.
    service, closeables = build_market_data_service(
        app.state.settings_service, app.state.secrets_service
    )
    app.state.market_data = service
    app.state.data_closeables = closeables
    logger.info("Market data providers: %s", service.provider_names)

    # AI layer (Phase 6) — provider built per request from settings + secrets so
    # a key entered in Settings takes effect without an engine restart.
    app.state.ai_service = AIService(
        app.state.settings_service,
        app.state.secrets_service,
        app.state.market_data,
        app.state.news_service,
        build_ai_provider,
    )
    logger.info("AI active provider: %s", app.state.ai_service.status().active_provider)

    # Global search + commentator (Phase 9).
    app.state.global_search_service = GlobalSearchService(
        app.state.symbol_universe, app.state.market_data
    )
    app.state.commentator_service = CommentatorService(
        app.state.news_service, app.state.ai_service
    )

    # Alerts (Phase 7) — a background monitor evaluates active alerts and
    # broadcasts fired ones over the WS hub to all connected clients.
    app.state.alert_service = AlertService()
    app.state.ws_hub = ConnectionHub()
    app.state.alert_monitor = AlertMonitor(
        app.state.alert_service, app.state.market_data, app.state.ws_hub
    )
    app.state.alert_monitor.start()
    logger.info("Alert monitor started")

    # Scheduler & reports (Phase 8) — APScheduler for morning summaries,
    # stocks-to-watch digest, and periodic news refresh.
    app.state.report_service = ReportService(
        app.state.market_data,
        app.state.news_service,
        app.state.watchlist_service,
        app.state.portfolio_service,
        app.state.settings_service,
        app.state.secrets_service,
        app.state.ws_hub,
    )
    app.state.scheduler_manager = SchedulerManager(
        JobContext(reports=app.state.report_service, news=app.state.news_service)
    )
    if settings.scheduler_enabled:
        app.state.scheduler_manager.start()
        logger.info("Background scheduler started")
    else:
        logger.info("Background scheduler disabled (BORSA_SCHEDULER_ENABLED=false)")

    yield

    app.state.scheduler_manager.stop()
    await app.state.alert_monitor.stop()
    for adapter in app.state.data_closeables:
        await adapter.aclose()
    logger.info("Engine shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"], summary="Liveness & version")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "providers": app.state.market_data.provider_names,
        }

    app.include_router(api_router)
    app.include_router(symbol_router)
    app.include_router(settings_router)
    app.include_router(watchlist_router)
    app.include_router(portfolio_router)
    app.include_router(news_router)
    app.include_router(ai_router)
    app.include_router(alert_router)
    app.include_router(scheduler_router)
    app.include_router(search_router)
    app.include_router(commentator_router)
    app.include_router(ws_router)
    return app


app = create_app()


def main() -> None:
    """Entry point for the PyInstaller bundle (``borsa-engine.exe``)."""
    import uvicorn

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "app.main:app",
        host=settings.engine_host,
        port=settings.engine_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
