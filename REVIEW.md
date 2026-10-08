# Skeptical interviewer review

Reviewed 2026-10-08. This distinguishes implemented behavior, exercised integrations and external blockers.

## CRITICAL

Resolved:

- Financial truth is backend-only. Hand fixtures verify compounding, monthly annualization, sample volatility, RF alignment, downside denominators, initial-wealth drawdowns, benchmark regression and capture definitions.
- Missing months do not become zero returns or falsely precise annualized risk. Critical unavailable constraints fail closed. Exact month joins and observation counts are retained.
- Hard eligibility is separate from scoring. Ineligible managers receive no score/rank, even with high returns. Stable tie-breaking and fixed scoring scales prevent cohort-dependent score shifts.
- Evidence is evaluation-scoped and immutable. Later mandates/market refreshes do not rewrite prior memo citations. Tests resolve every briefing citation and check old evidence after subsequent runs.
- No fake live data or AI. Synthetic fallback provenance is explicit. A real refresh initially exposed a French momentum header bug; it was fixed with a regression fixture containing the real explanatory-header shape. Yahoo, FRED and French then all reported successful live retrieval.
- Very long high-growth histories no longer overflow into invalid drawdowns/annualized metrics; log compounding preserves annualized growth and turns unrepresentable cumulative growth into null. Implausible monthly gains above 1000% are quarantined for unit review.

No remaining critical code defect was identified in the exercised scope.

## HIGH

Resolved:

- Clean PostgreSQL migration verified: upgrade, downgrade, re-upgrade and Alembic schema comparison in a new disposable database. No drift detected; disposable database removed.
- Entire Compose startup verified; backend and PostgreSQL healthy, nginx frontend serves the production bundle and proxies API requests.
- Synthetic demo reset restores cached fixtures after public refresh, preserving historical evaluations and raw uploads. Exact API flow verifies baseline, 7% drawdown exclusion for Atlas, monthly liquidity exclusion for Orion, and all 15 briefing claims.
- React compile/type errors fixed. Strict type check, ESLint and production build pass. Chart/icon chunks keep each generated JavaScript chunk below 500 kB.
- Dependency audit originally reported Tailwind transitive advisories. Updated Tailwind/PostCSS; npm audit reports zero vulnerabilities.
- Data Health now paginates the complete event ledger. CSV upload, idempotent duplicates, category filters, Universe search, manager metrics/charts, source-row drilldown, briefing creation and evidence filters were exercised in the browser.
- API key is backend-only, stored in ignored `.env`, never printed. Compose host ports bind only to loopback. Obsolete Tailwind v3 config and unused browser-test tooling removed.
- Empty-manager startup still initializes market fixtures so CSV ingestion does not depend on loading the synthetic manager universe.

**External blocker: real AI memo/challenge completion remains unverified.** The newly provisioned key reaches OpenAI, but the selected project returns HTTP 429 `credit_balance_exhausted`. This is API billing/quota, not authentication or a fabricated success. No live AI artifact was saved or represented as successful. Add API credit and run `docker compose exec backend python scripts/smoke_demo.py --ai` to complete live acceptance.

Provider-mocked tests exercise the full structured-output/validator/persistence path, numerical facts composed from deterministic evidence, challenge sections and citations. They do not establish live model quality or live structured-output compatibility. The app reports exhausted credit separately and preserves working evaluations and deterministic briefings.

## NICE TO HAVE

- Human-reviewed qualitative entailment evaluation. Citation existence and numeric/proper-name restrictions do not prove every interpretation follows from evidence. Confidence is model self-assessment.
- Wide CSV/metadata split-file ingestion, interactive resolution and source-mapping UI.
- Historical evaluation navigation, server-side audit pagination, robust/HAC regression errors and currency/serial-correlation adjustments.
- Fixed-layout PDF export and automated UI regression tests; current print layout is browser-dependent and UI checks are manual.
- More realistic empirical calibration of synthetic behaviors with explicitly licensed datasets. No claim of EDHEC calibration is made.
- Auth, durable background jobs, immutable tamper-resistant logging and concurrency hardening before real internal deployment.
- Current test stack emits a Starlette TestClient/httpx deprecation warning; tests pass, and it has no runtime impact on the served application.

## REMOVE RATHER THAN FIX

Removed unused Tailwind v3 config, unused Playwright test dependency, obsolete autoprefixer configuration, unused startup market-mode setting and generated TypeScript build metadata from deliverable scope. No Kafka, Redis, agent framework, BigQuery, GCP, institutional licensed-feed dependency or fake AI fixture is in the application.

## Verification record

| Check | Result |
| --- | --- |
| Backend pytest, packaged PostgreSQL environment | 32 passed |
| Backend Ruff | Passed |
| Frontend TypeScript, ESLint, production build | Passed |
| Dependency audit | Zero reported npm vulnerabilities |
| Clean PostgreSQL migrations, downgrade/re-upgrade, drift check | Passed |
| Docker Compose startup / healthy backend/database | Passed |
| Demo seed and exact deterministic API journey | Passed |
| Public Yahoo benchmarks, FRED macro/RF, French factors | All live providers succeeded after parser fix |
| Browser upload / Data Health / Universe / manager detail / mandate transitions / briefing / audit | Exercised successfully |
| Real OpenAI access | Reached API; exhausted project credit |
| Live AI narrative quality and complete challenge generation | Blocked by external quota; not claimed verified |

The complete deterministic journey is working. Full live-AI acceptance remains conditional on API project credit.
