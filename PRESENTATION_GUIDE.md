# Presenting Allocator IC Copilot

Prepared October 11, 2026. This guide compares the implementation with Option B: Allocator Memo Builder (IC Draft + Audit Trail). It reflects source inspection and the actual October 11 local-model acceptance recorded in REVIEW.md. Public market providers were not rechecked for this guide.

## Start with the problem

An allocator selects investment managers. An investment committee (IC) reviews the proposed decision. A mandate is the set of constraints that the selection must satisfy.

Use this opening:

> An allocator receives manager spreadsheets with inconsistent names, return formats and missing months. Before recommending anyone, they need to clean the data, compare performance with a benchmark, apply their investment constraints, and explain their decision to a committee. Allocator IC Copilot connects those steps and lets a reviewer trace memo claims back to calculations or original source fields.

The value is less manual reconciliation, clearer reasons for exclusions, and faster verification of the resulting draft. We have not measured time savings or conducted a finance-user usability study.

## A seven-minute presentation

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:45 | Problem and Overview | Define allocator, mandate and IC. Explain the workflow before discussing technology. The bundled 18-manager universe is synthetic. |
| 0:45–1:45 | Import Excel / CSV and Data Health | Show column mapping and validation preview. Explain missing values, duplicates, conflicting IDs, return units and gaps. Valid rows can remain usable while invalid rows are quarantined. Original files and corrections are retained. |
| 1:45–2:30 | Market source status and Universe | Explain return, volatility, drawdown, Sharpe and benchmark correlation in plain language. Refresh public sources if appropriate and report their actual status. Startup fixtures are synthetic; failed providers explicitly fall back to synthetic fixtures. |
| 2:30–3:45 | Decision Room | Load demo to establish the documented baseline. Start with quarterly liquidity and 15% drawdown tolerance. Tighten drawdown to 7%: eligible managers fall from 7 to 5. Change liquidity to monthly: 5 becomes 4. Explain that strong performance does not override a failed mandate. |
| 3:45–4:30 | Shortlist and one manager | Show suitability explanations, score contributions, source concerns and missing analyses. Rankings are deterministic policy outputs, not predictions. |
| 4:30–5:45 | IC Memo and evidence drawer | Generate a real AI memo with local Ollama, or use the explicitly labeled rules-based briefing. Click a metric citation, then a source-field citation. Show method, period and original row. A source note is traceable but remains unverified. |
| 5:45–6:15 | Excel and Word exports | Explain that exports are saved evaluation snapshots. Changes in Word or Excel do not sync back into the app. |
| 6:15–7:00 | Architecture and limits | Explain the backend/frontend/database split and bounded AI. Disclose the requirement gaps below. |

Use this sentence during the constraint change:

> The question is not just which manager performed best. It is which managers meet this mandate, and what evidence supports advancing them for diligence.

Demo preparation: use Load demo, inspect source status, and rehearse the 7 → 5 → 4 transition. Live refresh changes market inputs and can change rankings or eligibility, so do not promise the synthetic baseline counts after refreshing. Additional user imports are retained by Load demo and can also alter the candidate set. Identify the dataset actually present before presenting those counts.

Do not represent a rules-based briefing as LLM output. Real memo and challenge generation passed using local Qwen 2.5 through Ollama on October 11. The OpenAI provider still requires funded API access; its last request failed with exhausted project credit. Keep Ollama running and use the local Compose override for this demonstration. A configured provider alone does not establish runtime availability.

## Check against the original assignment

| Original requirement | Assessment | Evidence and qualification |
| --- | --- | --- |
| Web app from a messy fund universe to a defensible IC memo | Implemented core workflow | React workspace connects reviewed import, analytics, mandate, shortlist, memo and audit. Defensibility means visible methods and lineage, not verified investment truth. |
| CSV or a few CSVs with names, strategy, liquidity, fees, returns and notes | Mostly implemented | Monthly long-format CSV is supported; the legacy batch API accepts up to ten CSVs. Reviewed UI import handles one CSV/XLSX at a time. Fees and notes are optional source fields. Summary-stat-only datasets, wide monthly matrices and separate metadata/return-file joins are unsupported. |
| Mandate form with liquidity, target volatility, drawdown and strategies | Implemented with a UI qualification | Liquidity, volatility, drawdown, history, benchmark correlation, profile and strategy exclusions are exposed. Explicit preferred strategies/custom weights are supported by the API; the UI expresses soft preferences through profiles rather than individual preferred-strategy editing. |
| Normalize and validate missing values, date ranges and mismatched identifiers | Implemented | Required-field/format checks, exact ID canonicalization, metadata conflicts, duplicate handling, return/fee units, completed-month checks and history-gap flags. No fuzzy merging or missing-return imputation. Reviewed preview uses the real validator without persisting changes. |
| Pull public benchmark data | Implemented; startup is offline | Yahoo adjusted monthly prices for seven ETF proxies; FRED risk-free proxy/macro series; French explanatory factors. Public refresh is explicit. Earlier verification recorded successful retrieval from all providers. Actual status and synthetic fallback are displayed; availability today was not rechecked for this guide. |
| Drawdown, volatility, Sharpe and benchmark/peer correlation | Implemented | Backend owns financial calculations and exact monthly alignment. Benchmark correlation satisfies the benchmark-or-peers requirement; a peer correlation matrix is not necessary to claim this requirement. Unavailable critical inputs produce null and fail closed where required. |
| Use an LLM to produce a ranked shortlist with rationale | Partial literal match; deliberate architectural choice | Hard gates and weighted scoring determine the shortlist. The LLM must retain the eligible engine leader and cannot rank, calculate or change eligibility. It adds evidence-linked qualitative rationale, risks and diligence questions. Explain this split explicitly rather than claiming LLM-owned ranking. |
| LLM-generated 1–2 page IC memo: summary, recommendation, risks, appendix | Implemented and locally verified for the demo | Actual local-model generation saved 20 memo claims and six challenge claims with validated citations. The compact AI Word memo rendered in two pages; the challenge rendered in one. Full methods are available through a separate full-evidence export. Arbitrary uploaded content and browser printing do not have a universal page-count guarantee. |
| Audit view linking memo claims to metrics or source fields | Implemented with an interpretation limit | Claim IDs resolve to saved evaluation evidence, formulas, periods and source rows. Later evaluations do not rewrite earlier evidence. Citation validity does not prove that every AI interpretation logically follows from its evidence. |

## Explain the technical decisions

- **FastAPI, pandas and NumPy:** financial calculations and data validation live in one backend, which makes them testable and avoids conflicting browser calculations.
- **React and TypeScript:** interactive import review, constraint changes and evidence drilldown, with typed API contracts.
- **PostgreSQL, SQLAlchemy and Alembic:** relational identities and uniqueness checks, flexible snapshot metadata, and versioned schema changes.
- **Deterministic gates before scoring:** an ineligible manager cannot win through a high performance score. Scores use visible fixed scales and weights.
- **Evaluation-scoped evidence:** a memo retains the facts and sources used when it was created, even after another mandate or market refresh.
- **Provider boundaries and explicit fallback:** a public-data outage does not disable the demo or masquerade as live historical data.
- **Bounded structured output through local Ollama or OpenAI:** the model writes interpretations against selected evidence; validators reject unknown funds, invalid citations and unsupported numerical/ranking prose. Local generation uses constrained sections and reversible citation handles; its interpretation scope is source notes, while software supplies quantitative analysis. These restrictions trade expressive freedom for stronger controls, but do not establish semantic correctness.
- **Docker Compose:** reproducible frontend/backend/database startup without extra distributed infrastructure.

## Questions to prepare for

**Is this real fund data?** No. Bundled manager identities, notes and histories are synthetic. Public market data can be fetched live; offline market fixtures are also synthetic.

**Why not let AI choose the winners?** Mandate compliance and quantitative rankings need reproducible rules. AI helps explain and challenge the result, while the user can inspect the inputs and policy.

**Does an evidence link prove a claim is true?** It proves traceability. Source notes still need independent verification, and AI interpretations require human review.

**Is this ready for institutional deployment?** It is a working prototype. Authentication, production concurrency hardening, durable jobs, stronger logging and real-user acceptance remain future work. Simple liquidity frequencies do not represent every notice period, gate or lockup. There is no portfolio-level allocation optimizer.

## Remaining qualifications for the submission

1. Actual local-model memo/challenge acceptance and reviewed Word examples are complete. OpenAI-specific verification remains optional and requires funded access. Qualitative interpretations still need human review; the small local model is not independently validated investment reasoning.
2. The reviewed compact AI memo meets the two-page target; unusually long uploaded notes or other Word/browser renderers can change pagination. Full evidence is deliberately a longer optional export.
3. Document the deterministic-ranking/LLM-rationale split as an explicit interpretation of the brief; seek clarification only if the evaluator requires LLM-owned ranking.
4. Treat summary-stat-only ingestion and richer UI strategy preferences as remaining input/UI scope, not features already delivered.

Supporting documents: [README.md](README.md), [DATA_SOURCES.md](DATA_SOURCES.md), [ARCHITECTURE.md](ARCHITECTURE.md), [REVIEW.md](REVIEW.md).
