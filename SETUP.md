# Setup

## Start the app

You need Docker Desktop with Compose, Git, and available ports 5173 and 8000.

```sh
git clone https://github.com/abhishekreddy1206/allocator-ic-copilot.git
cd allocator-ic-copilot
[ -f .env ] || cp .env.example .env
docker compose up --build -d
```

Preserve an existing `.env`. Initial image and dependency downloads require network access.

Open [the app](http://localhost:5173), [backend health](http://localhost:8000/api/health), or [API documentation](http://localhost:8000/docs). Startup applies migrations and loads synthetic sample data. PostgreSQL runs in Docker; no separate installation is needed.

## Enable local AI

Install [Ollama](https://ollama.com/download), then start its app/server. If it is not already running:

```sh
ollama serve
```

In another terminal, from the project directory:

```sh
ollama pull qwen2.5:3b-instruct-q4_K_M
make up-local
```

Keep Ollama running. `make up-local` selects the local provider; use it for subsequent local-AI rebuilds. The Docker backend reaches the host through `host.docker.internal:11434`. Docker Engine on Linux may require a host-gateway address.

To use another installed model, set `OLLAMA_MODEL` in `.env` and rerun `make up-local`. The documented Qwen model completed actual memo and challenge generation on an Apple M3 Pro with 36 GB RAM. Performance varies by hardware and model.

For optional hosted inference, configure `AI_PROVIDER=openai` and `OPENAI_API_KEY` in `.env`, then run `make up`. Hosted generation requires available API credit. Never commit credentials. Provider selection is explicit; the app does not silently switch providers.

## Upload data

Choose **Import Excel / CSV**. Use one monthly observation per row, with headers in the first row. Required fields:

`fund_id`, `fund_name`, `strategy`, `liquidity`, `period`, `monthly_return`

Manager name, fees and qualitative notes are optional. Example:

```csv
fund_id,fund_name,strategy,liquidity,period,monthly_return
ALPHA,Alpha Macro,Global Macro,monthly,2024-01,1.2%
ALPHA,Alpha Macro,Global Macro,monthly,2024-02,0.012
```

Review column mappings, errors and warnings before confirming. Returns accept decimals or explicit percentages; dates must be unambiguous. The preview can edit the first 200 rows and validates up to 50,000 rows. Correct later rows in the source file. XLSX formulas, legacy XLS, wide monthly matrices and separate metadata/return joins are unsupported. Conflicting existing returns are flagged rather than overwritten.

Sample files and their provenance are listed in [DATA_SOURCES.md](DATA_SOURCES.md).

## Verify

```sh
make test
```

This builds a test image, starts a fresh PostgreSQL container, applies migrations and runs the full backend suite. It cleans up its own resources afterward and leaves the application database alone. It requires no `.env`, running app, local PostgreSQL, Node, Ollama or API key.

Additional checks:

| Command | Requirements and purpose |
| --- | --- |
| `make test-unit` | Python 3.12 environment with `backend/requirements.lock` installed; database-free tests using mocked providers |
| `make build` | Local Node 22.13+; install and build the frontend |
| `make lint` | Frontend dependencies installed and Compose backend running |
| `make smoke` | Running app; checks the fixed synthetic mandate journey |
| `make acceptance` | Running app and working AI provider; checks actual inference, saved citations and exports |

For the Python-only tests, create `.venv` with Python 3.12 and install `backend/requirements.lock` there. Bare full-suite `pytest` needs PostgreSQL; use `make test` for the self-contained integration environment.

Smoke and acceptance restore synthetic market inputs and expect 18 managers. Additional confirmed uploads can invalidate these fixed fixture assertions. Acceptance creates new saved evaluations and writes exports to ignored `artifacts/live-ai-acceptance/`.

## Develop and stop

With the Compose backend/database running:

```sh
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to localhost:8000. Use `API_PROXY` for another backend address. Host-based backend development needs Python 3.12, the locked dependencies and a PostgreSQL `DATABASE_URL`; host-based Ollama uses `http://localhost:11434`.

Run `docker compose down` to stop the app; saved data remains in its volume. Keep private files and exports in ignored `local-data/`, `uploads/`, `exports/` or `artifacts/`.

## Troubleshoot

| Problem | Check |
| --- | --- |
| App does not open | `docker compose ps` and `docker compose logs --tail 50 backend frontend`; check port conflicts |
| Local AI cannot connect | Ollama is running, the selected model is installed, and startup used `make up-local` |
| Hosted AI fails | Check API credentials, model access and available credit |
| AI output fails validation | The evaluation remains available; use the rules-based briefing and inspect the error |
| Public refresh partially fails | Inspect per-source status; failed sources retain labeled synthetic fallbacks |
