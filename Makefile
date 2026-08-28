.PHONY: install test lint format

install:
	python -m pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .
