# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-20

### Added
- Initial release: aiogram 3 bot for practising Part 1 of the OGE exam.
- Lightweight registration ("login"): name + school class.
- Catalog navigation: subject → month/variant → tasks.
- Automatic grading with `number` / `text` / `sequence` answer types.
- Image support per task via `image_url` or Telegram `image_file_id`.
- Per-attempt results with a task-by-task review and a user profile.
- Extensible YAML task banks under `data/`, loaded by `scripts/seed.py`.
- Admin commands `/reload` and `/stats`.
- Async SQLAlchemy 2.0 models, SQLite default, PostgreSQL support, Alembic setup.
- Optional Redis FSM storage.
- Docker + docker-compose, Makefile, ruff, pre-commit, GitHub Actions CI.
- Unit and integration tests (grading, loader, exam flow).
- FIPI parser skeleton (`scripts/parse_fipi.py`).

[Unreleased]: https://github.com/vladimirtrushin/OGE_Telegram_Bot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vladimirtrushin/OGE_Telegram_Bot/releases/tag/v0.1.0
