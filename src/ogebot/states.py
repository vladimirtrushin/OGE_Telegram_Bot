"""Finite-state-machine states for multi-step conversations."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    """Lightweight 'login': collect a display name and school class."""

    waiting_for_name = State()
    waiting_for_grade = State()


class Solving(StatesGroup):
    """Active exam session. Attempt/variant ids are kept in FSM data."""

    answering = State()
