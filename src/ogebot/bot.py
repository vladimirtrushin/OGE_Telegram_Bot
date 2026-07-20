"""Bot bootstrap: build the dispatcher, wire middlewares and run long-polling."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from ogebot.config import Settings, get_settings
from ogebot.db import create_engine, create_session_factory, dispose_engine, init_models
from ogebot.handlers import build_router
from ogebot.logging import get_logger, setup_logging
from ogebot.middlewares import DbSessionMiddleware, UserMiddleware

log = get_logger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start", description="Начать / регистрация"),
    BotCommand(command="menu", description="Выбрать предмет и вариант"),
    BotCommand(command="profile", description="Мой профиль и результаты"),
    BotCommand(command="about", description="Об авторе и контакты"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
    BotCommand(command="help", description="Справка"),
]


def _build_storage(settings: Settings) -> BaseStorage:
    if settings.use_redis:
        # Imported lazily so redis is only required when actually used.
        from aiogram.fsm.storage.redis import RedisStorage

        log.info("fsm_storage", backend="redis")
        return RedisStorage.from_url(settings.redis_url)
    log.info("fsm_storage", backend="memory")
    return MemoryStorage()


def build_dispatcher(settings: Settings, session_factory) -> Dispatcher:
    dp = Dispatcher(storage=_build_storage(settings))
    # Outer middlewares run for every update, in registration order.
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserMiddleware(settings))
    dp.include_router(build_router())
    # Values placed on the dispatcher are injected into handlers by name.
    dp["settings"] = settings
    return dp


async def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, json=settings.log_json)
    log.info("starting", database=settings.database_url.split("@")[-1])

    engine = create_engine(settings.database_url, echo=settings.sql_echo)
    session_factory = create_session_factory(engine)

    if settings.init_db_on_startup:
        await init_models(engine)
        log.info("db_ready")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher(settings, session_factory)

    try:
        await bot.set_my_commands(BOT_COMMANDS)
        me = await bot.get_me()
        log.info("bot_online", username=me.username, id=me.id)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await dispose_engine(engine)
        log.info("stopped")
