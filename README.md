# Allocator IC Copilot

Turn a messy fund universe into a ranked shortlist and an investment committee memo with traceable evidence.

Upload CSV or Excel data, set investment criteria, compare managers, and inspect the sources behind each memo claim. Financial calculations and rankings are deterministic; AI helps write interpretations and diligence questions.

## Run locally

Install and start Docker Desktop, then run:

```sh
git clone https://github.com/abhishekreddy1206/allocator-ic-copilot.git
cd allocator-ic-copilot
[ -f .env ] || cp .env.example .env
docker compose up --build -d
```

Open [localhost:5173](http://localhost:5173). The database and sample universe initialize automatically. No API key is needed for analytics, ranking, audit, or the rules-based briefing.

For AI memo generation, follow the local Ollama or optional OpenAI instructions in [SETUP.md](SETUP.md).

## Use the app

1. Explore the sample universe and **Market trends** on Overview, or choose **Import Excel / CSV**. Review validation results before confirming an import.
2. Check **Data Health**, then compare managers in **Universe**.
3. Set your investment criteria in **Decision Room** and review the **Shortlist**.
4. Create a draft in **IC Memo**, inspect citations in **Audit**, and export Word or Excel.

**Market trends** shows benchmark growth, 3- and 12-month returns, volatility, VIX and Treasury yields. Choose **Refresh public data** to retrieve newer inputs. Observation dates, live/synthetic labels and evidence links show what each saved evaluation used.

## Test

```sh
make test
```

Docker provisions a separate PostgreSQL test database automatically. No local PostgreSQL installation or AI credentials are required.

## Stack and data

React + TypeScript, FastAPI, pandas/NumPy, PostgreSQL, and optional Ollama or OpenAI inference.

The bundled universe contains **18 fictional managers and 1,007 accepted monthly observations**. Startup market fixtures are also synthetic. This is a research prototype; scores and memos support further diligence.

- [Setup and troubleshooting](SETUP.md)
- [Architecture and limitations](ARCHITECTURE.md)
- [Data sources and sample files](DATA_SOURCES.md)
