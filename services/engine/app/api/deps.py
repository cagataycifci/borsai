"""FastAPI dependency providers.

Services are constructed once at startup (see ``app.main``) and stored on
``app.state``. These helpers expose them to route handlers, keeping handlers
free of construction logic (dependency inversion).
"""

from __future__ import annotations

from fastapi import Request

from app.ai import AIService
from app.alerts import AlertService
from app.commentator import CommentatorService
from app.data.service import MarketDataService
from app.news import NewsService
from app.portfolio import PortfolioService
from app.scheduler import ReportService, SchedulerManager
from app.search import GlobalSearchService
from app.settings.service import SecretsService, SettingsService
from app.watchlists import WatchlistService


def get_market_data(request: Request) -> MarketDataService:
    return request.app.state.market_data


def get_settings_service(request: Request) -> SettingsService:
    return request.app.state.settings_service


def get_secrets_service(request: Request) -> SecretsService:
    return request.app.state.secrets_service


def get_symbol_universe(request: Request):
    return request.app.state.symbol_universe


def get_watchlist_service(request: Request) -> WatchlistService:
    return request.app.state.watchlist_service


def get_portfolio_service(request: Request) -> PortfolioService:
    return request.app.state.portfolio_service


def get_news_service(request: Request) -> NewsService:
    return request.app.state.news_service


def get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service


def get_alert_service(request: Request) -> AlertService:
    return request.app.state.alert_service


def get_report_service(request: Request) -> ReportService:
    return request.app.state.report_service


def get_scheduler_manager(request: Request) -> SchedulerManager:
    return request.app.state.scheduler_manager


def get_global_search_service(request: Request) -> GlobalSearchService:
    return request.app.state.global_search_service


def get_commentator_service(request: Request) -> CommentatorService:
    return request.app.state.commentator_service
