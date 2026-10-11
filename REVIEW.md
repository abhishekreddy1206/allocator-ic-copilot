# Skeptical interviewer review

Reviewed 2026-10-08. This distinguishes implemented behavior, exercised integrations and external blockers.

**October 11 update:** real local-model memo and challenge acceptance now pass using Ollama with Qwen 2.5. The original OpenAI credit blocker remains specific to that provider. See the final acceptance record below; earlier sections are dated build history.

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

**Historical OpenAI blocker:** the newly provisioned key reached OpenAI, but the selected project returned HTTP 429 `credit_balance_exhausted`. This was API billing/quota, not authentication or a fabricated success. No OpenAI artifact was saved or represented as successful. October 11's live AI acceptance uses the explicitly selected local provider instead; OpenAI-specific live acceptance still requires funded API access.

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

At the initial review, the deterministic journey worked and live-AI acceptance remained conditional on API project credit. The local-provider acceptance recorded below supersedes that general AI blocker.

## Finance usability update verified October 9 2026

Added a CSV/XLSX review flow with worksheet selection, explicit column mapping, cell corrections, real-validator previews inside rolled-back savepoints, and a separate confirmed commit. The additive migration preserves original file bytes, original-source SHA-256, sheet, mapping, and correction history. Existing accepted returns remain immutable; conflicting revisions are quarantined. Original-source downloads and source-row evidence include the reviewed context. Existing CSV API clients remain compatible.

Added backend suitability summaries to new evaluations and surfaced them ahead of score details. They use actual hard-gate outcomes and score contributions, identify unverified source concerns and missing analyses, and count only unresolved warning/error events as follow-up work. Historical runs remain unchanged and render a reevaluation prompt when the new summary is absent. Reviewed imports of the known synthetic dataset retain synthetic labeling through the original-source digest.

Added an Excel comparison snapshot for all managers, with numeric metrics, explicit Yes/No eligibility, synthetic/uploaded labels, observation windows, reasons, concerns, evidence IDs, mandate context and source status. Names and notes are stored as literal strings to prevent formula injection. Added editable Word exports of saved memos or deterministic briefings, with evidence references and methodology appendix. Export failures do not mutate evaluations and exports never call AI or recalculate finance.

Validation: 36 backend tests passed; the four import/export tests passed again after final formatting and labeling edits. Ruff, frontend typecheck/lint/build, Alembic schema check, and the original demo smoke passed. Browser verification covered XLSX upload, missing-field mapping, correction, preview refresh, confirmation, Data Health refresh, suitability cards, and an actual Excel download. The final Word export was rendered and all three pages inspected; both Excel sheets were rendered and reviewed. Live AI quota remains the previously documented limitation.

Remaining limitations: first-row headers and monthly long format are required; the first 200 rows are editable in the preview and at most 300 prioritized issues appear there. XLS/XLSM, workbook formula evaluation, PDF extraction, wide-format returns and revisions to accepted returns are unsupported. Exports are editable/static snapshots without round-trip synchronization. No portfolio-level allocation analysis, firm-specific document templates, or user usability study has been added.

## Live local AI acceptance October 11 2026

Provider: **Ollama local inference**. Actual installed model: `qwen2.5:3b-instruct-q4_K_M`, Ollama 0.24.0, Apple M3 Pro host with 36 GB memory. No paid API request is used in this mode. A fresh OpenAI attempt still reported exhausted project credit before the provider switch.

Command: `docker compose exec backend python scripts/smoke_demo.py --ai --output-dir /tmp/live-ai-acceptance`, after starting with `compose.yaml` plus `compose.ollama.yaml`.

Final successful evaluation: `74292b22-5433-41b5-8cc7-5596a45ee27d`.

| Acceptance check | Actual result |
| --- | --- |
| Synthetic baseline and mandate transitions | Passed; drawdown and liquidity exclusions retained |
| Deterministic briefing | 15 claims; all citations resolved |
| Actual model-generated memo | 20 total claims: deterministic facts plus five generated interpretation/diligence claims; saved memo `37d0c314-c951-42ef-9bd0-deb5aa84662a` |
| Actual model-generated challenge | Six generated claims across four sections, including three separate diligence questions; saved challenge `5026a7c3-b807-41c7-b82e-3d250774ec39` |
| Output validation | Both passed on their first validation attempt in the final run |
| Persistence | GET `/api/memos` returned each saved ID and identical payload |
| Citations | Every claim had references; every reference resolved and belonged to the same saved evaluation; full application validation checked fund ownership |
| Export endpoints | Both compact and full-evidence Word responses downloaded and had valid DOCX ZIP signatures |
| Quantitative input status | Explicitly CACHED DEMO DATA; this acceptance does not claim live historical manager or benchmark data |

Actual model usage: memo 1,227 input / 404 output tokens. The local model interprets selected source notes; the saved briefing supplies quantitative/factor facts and ranking. Challenge interpretation is restricted to the leader's source note. Provider, model, context scope and usage are persisted with each artifact.

Real inference exposed issues missed by mocked tests: runtime truncation of the original full evidence context, repeated manager names, incorrect citation ownership, and grouped diligence questions. The local adapter now sends bounded note-based context, separates the synthetic marker from investment content, uses reversible identity/citation handles, constrains sections/question counts in JSON Schema, and maps handles back before the unchanged financial/citation validators run. Rejected attempts did not erase evaluations or save accepted AI artifacts.

Human review also found hedge questions citing liquidity: links resolved but the field did not support the question. The final challenge exposes only the relevant source-note evidence. Its hypothetical hedge improvements remain interpretation, not established capability. This scoped correction does not establish arbitrary semantic entailment; human review remains necessary.

Compact exports retain numbered reference suffixes plus the shared evaluation ID; full methods and source records remain in Audit and the separately requested full-evidence export. [Actual AI memo example](docs/examples/ai-memo.docx) and [actual challenge example](docs/examples/ai-challenge.docx) are snapshots from the final successful run. Their evidence IDs refer to that saved local evaluation, not a fresh clone's database. Page counts are renderer/content dependent; the rendered examples are reviewed below.

Document QA: the actual AI memo rendered in **two pages** and the actual challenge in **one page** using the bundled Word renderer. Every page was visually inspected; headings, citations and source references were readable and unclipped. This is evidence for these examples, not a universal pagination guarantee for arbitrary uploaded notes or browser printing.

Regression verification: 37 backend tests passed; the 16 provider/import/export tests passed again after the final scope refinement. Ruff passed. Frontend TypeScript, ESLint and production build passed. The existing Starlette/httpx deprecation warning remains non-blocking.

Browser verification: Generate AI memo and Challenge Recommendation created additional persisted local-model artifacts (`abcc3878-8ee4-4637-bc26-8ebb1e124940` and `59646502-9cb0-4acc-b668-021c8a00559b`). An AI claim opened its saved source evidence and original CSV row 321, showing the synthetic manager note, original units and source digest. Screenshots: [AI memo](docs/live-ai-memo.png), [claim to original source](docs/live-ai-evidence.png).
