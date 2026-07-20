"""Console entrypoint: ``python -m ogebot`` / ``ogebot``."""

from __future__ import annotations

import asyncio
import contextlib

from ogebot.bot import run


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(run())


if __name__ == "__main__":
    main()
