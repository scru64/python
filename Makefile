.PHONY: build lint test

build: lint test
	poetry build

lint:
	black --check scru64 tests
	mypy --strict scru64 tests

test:
	python -m unittest -v
