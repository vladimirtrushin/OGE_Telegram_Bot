"""Cross-cutting handlers: /cancel and a friendly fallback for stray messages."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ogebot import texts

router = Router(name="common")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer(texts.NOTHING_TO_CANCEL)
        return
    await state.clear()
    await message.answer(texts.CANCELLED)


@router.message()
async def fallback(message: Message) -> None:
    """Any message not handled by a feature router lands here."""
    await message.answer(
        "Не совсем понял 🤔\nОткрой каталог вариантов командой /menu или посмотри справку /help."
    )
