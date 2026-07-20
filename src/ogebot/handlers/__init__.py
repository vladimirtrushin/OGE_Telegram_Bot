"""Handler routers, aggregated for registration on the dispatcher."""

from __future__ import annotations

from aiogram import Router

from ogebot.handlers import admin, catalog, common, exam, start


def build_router() -> Router:
    """Combine all feature routers into a single root router.

    Order matters: ``common`` is last so its catch-all fallback only fires when
    no feature router handled the update.
    """
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(catalog.router)
    root.include_router(exam.router)
    root.include_router(admin.router)
    root.include_router(common.router)
    return root


__all__ = ["build_router"]
