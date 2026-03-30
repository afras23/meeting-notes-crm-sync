.PHONY: install install-dev lint format typecheck test evaluate run docker compose-up compose-down

PYTHONPATH ?= .

install:
	python -m pip install -r requirements.txt

install-dev: install
	python -m pip install -r requirements-dev.txt

lint:
	PYTHONPATH=$(PYTHONPATH) ruff check app tests scripts eval
	PYTHONPATH=$(PYTHONPATH) ruff format --check app tests scripts eval

format:
	ruff format app tests scripts eval

typecheck:
	PYTHONPATH=$(PYTHONPATH) mypy app tests scripts eval

test:
	PYTHONPATH=$(PYTHONPATH) pytest tests -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=80

evaluate:
	PYTHONPATH=$(PYTHONPATH) python scripts/evaluate.py

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker:
	docker build -t meeting-notes-crm-sync:local .

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v
