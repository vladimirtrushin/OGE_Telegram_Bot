.DEFAULT_GOAL := help
.PHONY: help install dev seed run lint fmt test migrate revision docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install the package (runtime deps only)
	pip install -e .

dev: ## Install with dev + parse extras and pre-commit hooks
	pip install -e ".[dev,parse]"
	pre-commit install

seed: ## Load YAML task banks into the database
	python scripts/seed.py

run: ## Start the bot (long polling)
	python -m ogebot

lint: ## Run ruff checks
	ruff check .

fmt: ## Auto-format and fix with ruff
	ruff check --fix .
	ruff format .

test: ## Run the test suite
	pytest -q

migrate: ## Apply all Alembic migrations
	alembic upgrade head

revision: ## Autogenerate a migration (make revision m="message")
	alembic revision --autogenerate -m "$(m)"

docker-up: ## Build and start the full stack (bot + postgres + redis)
	docker compose up --build

docker-down: ## Stop the stack
	docker compose down
