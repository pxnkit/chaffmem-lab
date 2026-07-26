.PHONY: install test lint smoke reproduce web docker

install:
	python -m pip install -e ".[dev]"
	npm ci

test:
	pytest
	npm test

lint:
	ruff check src tests
	mypy src
	npm run lint

smoke:
	chaffmem run configs/benchmark/smoke.yaml

reproduce:
	python scripts/reproduce_reference.py

web:
	npm run dev

docker:
	docker compose up --build
