# Design decisions

- PostgreSQL rather than SQLite: relational uniqueness, transaction semantics, JSONB and a reviewer-reproducible datastore through Compose. Tests exercise PostgreSQL too.
- Pure finance functions: compounding and monthly annualization are explicit, testable and independent of AI or HTTP.
- Providers: Yahoo adjusted monthly prices, FRED short Treasury proxy, French factor files; each independently falls back to clearly synthetic cached demo series. Offline fixtures are not historical observations.
- No BigQuery/GCP/Bloomberg dependency: unnecessary deployment/licensing friction. Interfaces allow future licensed sources.
- Eligibility before ranking: a hard breach cannot be redeemed by high returns. Unknown critical metrics fail closed.
- Fixed bounded scoring transforms rather than cohort min/max: peer removals cannot change remaining component scores. Visible profile weights are subjective decision preferences.
- Evidence-bound AI: no LLM calculation, no invented funds, no unsupported numbers. Conservative output policy prohibits numeric prose; quantitative facts are rendered directly from evidence. Source notes are untrusted input.
- Immutable evaluation evidence: source return IDs, market observation IDs, methodology and data coverage accompany each metric. Old memos remain linked to old runs.
- Missing months: retained gaps, never zero filled. Annualized growth/risk are suppressed for discontinuous histories; aligned relative metrics remain available with explicit counts. Hard risk mandates fail closed.
- Optional enrichment isolation: network and AI failures preserve ingestion/evaluation. A deterministic briefing is explicitly labeled, never presented as an AI response.
