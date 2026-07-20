"""Seed (or refresh) the database from the YAML task banks in ``data/``.

Usage:
    python scripts/seed.py                # uses DATA_DIR / ./data
    python scripts/seed.py path/to/data   # custom directory

Idempotent: safe to run repeatedly. Existing variants are fully replaced.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make ``src`` importable when running from a source checkout without install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ogebot.config import get_settings  # noqa: E402
from ogebot.db import (  # noqa: E402
    create_engine,
    create_session_factory,
    dispose_engine,
    init_models,
)
from ogebot.logging import setup_logging  # noqa: E402
from ogebot.services.loader import load_directory  # noqa: E402


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, json=settings.log_json)

    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.data_dir
    if not data_dir.exists():
        raise SystemExit(f"Data directory not found: {data_dir.resolve()}")

    engine = create_engine(settings.database_url, echo=settings.sql_echo)
    await init_models(engine)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            count = await load_directory(session, data_dir)
            await session.commit()
        print(f"✓ Loaded {count} variant(s) from {data_dir.resolve()}")
    finally:
        await dispose_engine(engine)


if __name__ == "__main__":
    asyncio.run(main())
