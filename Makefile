.DEFAULT_GOAL := help
SHELL := /bin/bash

VENV   := venv/bin
PYTHON := $(VENV)/python
PIP    := $(VENV)/pip
ARGS   ?=

.PHONY: help install serve serve-no-browser dev build test test-backend test-frontend coverage check docs docs-build screenshots clean

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	$(PIP) install -e ".[dev]"
	cd frontend && npm install

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

serve: build ## Build frontend then start server (ARGS= to pass flags)
	$(PYTHON) -m talekeeper serve $(ARGS)

serve-no-browser: build ## Build frontend then start server without opening browser
	$(PYTHON) -m talekeeper serve --no-browser $(ARGS)

dev: ## Start backend in reload mode (no frontend build)
	$(PYTHON) -m talekeeper serve --reload --no-browser $(ARGS)

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build: ## Build the frontend
	cd frontend && npm run build

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests (pytest)
	$(PYTHON) -m pytest $(ARGS)

test-frontend: ## Run frontend tests (vitest)
	cd frontend && npm run test $(ARGS)

coverage: ## Run backend tests with coverage
	$(PYTHON) -m pytest -v --cov $(ARGS)

check: ## Run frontend type checking (svelte-check)
	cd frontend && npm run check

# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------

docs: docs-build ## Build and serve documentation locally
	$(PYTHON) -m http.server -d site 8080

docs-build: ## Build documentation with zensical
	$(VENV)/zensical build

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

screenshots: ## Capture screenshots for the user guide
	$(PYTHON) scripts/take_screenshots.py $(ARGS)

clean: ## Remove build artifacts
	rm -rf frontend/build frontend/dist src/talekeeper/static site
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
