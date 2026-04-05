.PHONY: help install install-dev lint format typecheck test evaluate run docker compose-up compose-down migrate clean

PYTHONPATH ?= .

help: ## Print available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}' | sort

install: ## Install production dependencies
	python -m pip install -r requirements.txt

install-dev: install ## Install dev dependencies (includes production)
	python -m pip install -r requirements-dev.txt

lint: ## Run Ruff lint and format check
	PYTHONPATH=$(PYTHONPATH) ruff check app tests scripts eval
	PYTHONPATH=$(PYTHONPATH) ruff format --check app tests scripts eval

format: ## Auto-format with Ruff
	ruff format app tests scripts eval

typecheck: ## Run mypy
	PYTHONPATH=$(PYTHONPATH) mypy app tests scripts eval

test: ## Run pytest with coverage gate
	PYTHONPATH=$(PYTHONPATH) pytest tests -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=80

evaluate: ## Run evaluation harness (scripts/evaluate.py)
	PYTHONPATH=$(PYTHONPATH) python scripts/evaluate.py

run: ## Start API with uvicorn (reload)
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker: ## Build local Docker image
	docker build -t meeting-notes-crm-sync:local .

compose-up: ## docker compose up (detached, build)
	docker compose up -d --build

compose-down: ## docker compose down (remove volumes)
	docker compose down -v

migrate: ## Apply Alembic migrations
	alembic upgrade head

clean: ## Remove caches, coverage artifacts, and bytecode
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
