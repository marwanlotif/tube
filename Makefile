SHELL := /bin/bash
.DEFAULT_GOAL := run
.PHONY: install build run test lint clean

DIST := frontend/dist/index.html
FRONTEND_SRC := $(shell find frontend/src frontend/index.html frontend/vite.config.ts \
	frontend/tsconfig.json frontend/package.json -type f 2>/dev/null)

install:
	cd backend && uv sync
	cd frontend && npm ci

build:
	cd frontend && npm run build

$(DIST): $(FRONTEND_SRC)
	@if ! command -v npm >/dev/null 2>&1; then \
		if [ -f "$(DIST)" ]; then \
			echo "Warning: frontend sources changed, but npm is not installed. Using the existing build." >&2; \
			exit 0; \
		fi; \
		echo "Tube's frontend is not built and npm is not installed." >&2; \
		echo "Run 'make install && make build' on a machine with Node.js, then copy the repo." >&2; \
		exit 1; \
	fi; \
	[ -d frontend/node_modules ] || (cd frontend && npm ci); \
	cd frontend && npm run build

run: $(DIST)
	@command -v uv >/dev/null 2>&1 || { echo "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2; exit 1; }
	cd backend && uv run vid-dwn $(ARGS)

test:
	cd backend && uv run pytest -q
	cd backend && uv run ruff check app

lint:
	cd backend && uv run ruff check app
	cd frontend && npx tsc --noEmit

clean:
	rm -rf frontend/dist
	find backend -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
