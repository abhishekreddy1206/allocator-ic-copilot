.PHONY: up demo test build lint
up:
	docker compose up --build -d
demo:
	curl --fail -X POST http://localhost:8000/api/demo
test:
	docker compose exec backend pytest -q
build:
	cd frontend && npm ci && npm run build
lint:
	cd frontend && npm run lint
	docker compose exec backend ruff check app tests
