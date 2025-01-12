.PHONY: build lint test

build: lint test
	poetry build

lint:
	poetry run black --check scru64 tests
	poetry run mypy --strict scru64 tests

test:
	poetry run python -m unittest -v
