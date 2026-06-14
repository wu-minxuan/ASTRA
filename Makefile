.DEFAULT_GOAL := help

.PHONY: help check-uv check-npm setup test test-unit test-integration test-frontend test-e2e check dev-backend dev-frontend

BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_DIR ?= frontend
NPM ?= npm
PYTHON_USER_BASE ?= $(shell python3 -m site --user-base 2>/dev/null)
PYTHON_USER_BIN ?= $(if $(PYTHON_USER_BASE),$(PYTHON_USER_BASE)/bin,)
UV ?= $(shell command -v uv 2>/dev/null || if [ -n "$(PYTHON_USER_BIN)" ] && [ -x "$(PYTHON_USER_BIN)/uv" ]; then printf '%s\n' "$(PYTHON_USER_BIN)/uv"; fi)
UV_CACHE_DIR ?= .uv-cache
export UV_CACHE_DIR

help:
	@echo "ASTRA development commands:"
	@echo "  make setup             Install backend/frontend dependencies and Playwright Chromium"
	@echo "  make test              Run backend unit and integration tests"
	@echo "  make test-unit         Run backend unit tests"
	@echo "  make test-integration  Run backend integration tests"
	@echo "  make test-frontend     Run frontend lint and build"
	@echo "  make test-e2e          Run Playwright browser E2E tests"
	@echo "  make check             Run static checks, backend tests, frontend checks, and E2E"
	@echo "  make dev-backend       Start FastAPI on $(BACKEND_HOST):$(BACKEND_PORT)"
	@echo "  make dev-frontend      Start Vite on 127.0.0.1:5173"

check-uv:
	@[ -n "$(UV)" ] && command -v "$(UV)" >/dev/null 2>&1 || (echo "uv not found. Install uv and ensure it is on PATH, or run make UV=/path/to/uv <target>."; exit 1)

check-npm:
	@command -v $(NPM) >/dev/null 2>&1 || (echo "npm not found. Install Node.js/npm and ensure npm is on PATH, or run make NPM=/path/to/npm <target>."; exit 1)

setup: check-uv check-npm
	$(UV) sync
	cd $(FRONTEND_DIR) && $(NPM) install
	cd $(FRONTEND_DIR) && npx playwright install chromium

test: check-uv
	$(UV) run pytest tests/unit tests/integration

test-unit: check-uv
	$(UV) run pytest tests/unit

test-integration: check-uv
	$(UV) run pytest tests/integration

test-frontend: check-npm
	cd $(FRONTEND_DIR) && $(NPM) run lint
	cd $(FRONTEND_DIR) && $(NPM) run build

test-e2e: check-uv check-npm
	cd $(FRONTEND_DIR) && ASTRA_UV="$(UV)" $(NPM) run test:e2e

check: check-uv check-npm
	$(UV) run ruff check .
	$(UV) run pytest tests/unit tests/integration
	cd $(FRONTEND_DIR) && $(NPM) run lint
	cd $(FRONTEND_DIR) && $(NPM) run build
	cd $(FRONTEND_DIR) && ASTRA_UV="$(UV)" $(NPM) run test:e2e

dev-backend: check-uv
	PYTHONPATH=src $(UV) run uvicorn astra.api.app:app --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

dev-frontend: check-npm
	cd $(FRONTEND_DIR) && $(NPM) run dev
