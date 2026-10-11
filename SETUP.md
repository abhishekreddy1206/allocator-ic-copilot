# Setup and run instructions

The verified AI workflow uses Qwen 2.5 locally through Ollama. The bundled manager histories and startup market fixtures are synthetic. Public market retrieval is a separate action.

This document owns installation, configuration, verification commands and troubleshooting. For the product and architecture, see [README.md](README.md); for the timed walkthrough, see [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md).

## Prerequisites

- Docker Desktop with Docker Compose running; ports 5173 and 8000 available.
- Git and Make for the commands below. Equivalent Docker commands are listed in the Makefile.
- For local AI, install [Ollama](https://ollama.com/download). The verified host was an Apple M3 Pro with 36 GB memory; model speed and hardware requirements vary.
- Network access for initial image, dependency and model downloads. After installation, the synthetic demo and local AI do not require hosted API credits.

## Start the application

```sh
git clone https://github.com/abhishekreddy1206/allocator-ic-copilot.git
cd allocator-ic-copilot
[ -f .env ] || cp .env.example .env
```

If the project already exists, use that checkout and preserve its existing `.env`.

For analytics and the rules-based briefing:

```sh
make up
```

For the verified local AI workflow, start Ollama in one terminal (skip this if its app/server is already running):

```sh
ollama serve
```

In a second terminal, from the project directory:

```sh
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama list
make up-local
```

`make up-local` selects the local provider through `compose.ollama.yaml` and waits for the application services to become healthy. Keep Ollama running. Use this target for subsequent local-AI rebuilds; `make up` selects the default Compose configuration.

Open [the app](http://localhost:5173/). Check [backend health](http://localhost:8000/api/health) or [API documentation](http://localhost:8000/docs). Migrations, synthetic seed and initial evaluation run automatically.

Docker Desktop reaches Ollama through `http://host.docker.internal:11434`. For a backend running directly on the host, use `OLLAMA_BASE_URL=http://localhost:11434`. Docker Engine on Linux needs an appropriate host-gateway or runtime address. Configure `OLLAMA_MODEL` in local `.env` to use another installed model, then recreate the backend with `make up-local`; only the documented Qwen model has the recorded live acceptance.

## Verify the workflow

### Reviewer tests on a new machine

With Docker running, the complete backend test suite needs only the checkout:

```sh
make test
```

This command builds the backend test image, starts a fresh PostgreSQL 16 container, waits for database readiness, applies Alembic migrations, and runs the suite. It uses a unique Compose project and cleans up its own containers/network/anonymous database volume afterward, including after test failure. It does not require the application to be running, a local PostgreSQL installation, `.env`, Node, Ollama, or API credentials. Initial image/dependency downloads require network access. Application database volumes are separate and remain untouched.

If Docker/PostgreSQL is unavailable, run the database-free unit subset with Python 3.12:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
make test-unit
```

These tests exercise analytics, mandate rules, provider fixtures and AI validation with mocked inference. They do not verify ingestion persistence, PostgreSQL constraints, transactions or database-backed API behavior. To use an existing Python environment, run `make test-unit BACKEND_PYTHON=python3.12` after installing dependencies there. Dependencies are still required even when no database server is needed.

Running bare `pytest` over the full suite on the host still requires a reachable PostgreSQL instance through `DATABASE_URL`. Synthetic manager/test fixtures supply records; they do not replace a database engine. Prefer `make test` for integration coverage instead of swapping PostgreSQL for SQLite or silently skipping failures.

### Application and real-model acceptance

```sh
make test
make lint
make build
make smoke
make acceptance
```

`make build` needs local Node 22.13 or later; Docker startup already builds the frontend with its packaged runtime. Frontend lint also uses local Node. `make lint`, `make smoke` and `make acceptance` require the application backend to be running; `make test` independently provisions its test database.

`make smoke` exercises the deterministic mandate journey. `make acceptance` additionally performs actual memo and challenge generation, checks persisted payloads and evaluation-owned citations, and downloads JSON plus compact/full-evidence Word exports into `artifacts/live-ai-acceptance/`. This directory is ignored by Git. `make smoke-ai` runs the same AI journey without copying exports out.

Acceptance restores synthetic market fixtures and the baseline mandate, retains uploads and prior runs, and asserts the documented 18-manager universe. Additional imported managers can invalidate those fixed demo assertions; do not delete real uploads merely to force a passing demo. Repeated acceptance creates new evaluation/artifact snapshots.

For browser verification, open IC Memo, generate an AI memo, generate the challenge, and click an evidence marker. Source-field citations can open the original uploaded row. The availability flag means a provider is configured; generation itself establishes whether the server/model is working.

Expected acceptance output includes successful baseline/mandate transitions, resolved briefing citations, live memo and challenge counts, and `Demo journey passed`. Claim counts can vary with provider/model output; do not treat a specific count as a universal requirement. [REVIEW.md](REVIEW.md) records actual results and evaluation IDs. Curated examples in `docs/examples/` are tracked snapshots; `make acceptance` creates fresh local artifacts.

## Backend and frontend development

Use Python 3.12 and Node 22.13 or later. Docker supplies supported runtimes for the normal application startup.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api` to localhost:8000. Keep the Compose backend/database running, or configure `DATABASE_URL` for a development PostgreSQL when running the backend separately. For a different proxy destination, set `API_PROXY` when starting Vite. There is no SQLite fallback. In host-based local AI development, use `OLLAMA_BASE_URL=http://localhost:11434`.

Startup runs Alembic, seeds the synthetic dataset idempotently and creates an evaluation. `SEED_DEMO=false` disables automatic manager loading; `make demo` or `./scripts/seed-demo.sh` loads it explicitly. PostgreSQL state persists in the Docker volume.

## Use public market observations

Click **Refresh public data**, inspect each provider's actual live/fallback status, then generate a new memo for that evaluation. Failed providers retain explicitly labeled synthetic fallback. Clicking **Load demo** restores synthetic fixtures.

The smoke script's `--refresh` option checks public retrieval before resetting the demo for fixed assertions. Therefore, the script's subsequent AI memo uses synthetic demo market inputs even with `--refresh --ai`.

## Optional OpenAI mode

OpenAI remains supported. Configure `AI_PROVIDER=openai`, `OPENAI_API_KEY` and optional `OPENAI_MODEL` in ignored `.env`, then use `make up` to recreate the default backend configuration. API access must be funded; the last recorded OpenAI attempt failed because the selected project exhausted its credit. Never paste keys into documentation or commit `.env`. Local Ollama mode does not call OpenAI or Meta.

## Troubleshooting and stopping

| Symptom | Check |
| --- | --- |
| Local AI fails to connect | Confirm Ollama is running, the backend is in local mode, and its runtime URL matches host/Docker networking. |
| Model is unavailable | Run `ollama list`; pull the exact configured model name. |
| AI validation fails | The app preserves the evaluation and briefing. Inspect the sanitized error and backend logs; do not bypass citation or factual validators. |
| OpenAI reports exhausted credit | Fund the API project or use `make up-local` with Ollama. Repeated retries do not replenish credit. |
| Public data refresh partially fails | Inspect per-source status. A mixed live/synthetic result is explicitly labeled. |
| App is unavailable | Run `docker compose ps` and `docker compose logs --tail 50 backend frontend`; check port conflicts. |

Stop application containers with `docker compose down`; saved data remains in the Docker volume. Stop a foreground Ollama server with Ctrl+C when finished. A Docker service restart does not start Ollama on the host.

Keep private input files in ignored `uploads/` or `local-data/`; put local exports in ignored `exports/` or `artifacts/`. Follow [README.md](README.md) for supported import formats, limitations and architecture, and [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md) for the demo narrative.

The tracked `.env.example` is a template. Preserve an existing `.env` when following setup commands. OS metadata, dependency/build/test caches, local artifact/data directories and model weights are ignored. Synthetic fixtures, reviewed screenshots, curated `docs/examples/` documents and migration SQL are intentionally tracked; avoid blanket ignores for CSV, XLSX, DOCX or SQL files.
