BACKEND_PYTHON ?= $(CURDIR)/.venv/bin/python
.PHONY: up up-local demo smoke smoke-ai acceptance test test-unit build lint
up:
	docker compose up --build -d
up-local:
	docker compose -f compose.yaml -f compose.ollama.yaml up --build -d --wait
demo:
	curl --fail -X POST http://localhost:8000/api/demo
smoke:
	docker compose exec -T backend python scripts/smoke_demo.py
smoke-ai:
	docker compose exec -T backend python scripts/smoke_demo.py --ai
acceptance:
	docker compose exec -T backend python scripts/smoke_demo.py --ai --output-dir /tmp/live-ai-acceptance
	mkdir -p artifacts/live-ai-acceptance
	docker compose cp backend:/tmp/live-ai-acceptance/. artifacts/live-ai-acceptance/
test:
	sh scripts/test-backend.sh
test-unit:
	cd backend && "$(BACKEND_PYTHON)" -m pytest -q tests/test_analytics.py tests/test_mandates.py tests/test_providers_ai.py tests/test_market_context.py
build:
	cd frontend && npm ci && npm run build
lint:
	cd frontend && npm run lint
	docker compose exec backend ruff check app tests
