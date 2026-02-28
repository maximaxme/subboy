from .start import router as start_router
from .subscriptions import router as subscriptions_router
from .categories import router as categories_router
from .reports import router as reports_router
from .settings import router as settings_router

__all__ = [
    "start_router",
    "subscriptions_router",
    "categories_router",
    "reports_router",
    "settings_router",
]
