# Implementation plan

1. Document contracts; scaffold Compose, database models, migration and backend dependencies.
2. Build pure finance/OLS, strict CSV ingestion, seeded market fixtures and structured manager scenarios.
3. Complete vertical slice: demo seed → persisted universe → evaluation → React Decision Room.
4. Add external providers and lineage, evidence detail, factor/regime charts and deterministic briefing.
5. Add optional structured Responses memo/challenge with conservative claim validation.
6. Verify finance hand fixtures, validation failures, provider fallback, clean PostgreSQL migration, demo transitions, browser interaction, frontend type/lint/build and Compose health. Record limitations honestly in REVIEW.md.

Verification matrix: unit calculations; malformed/multi-file CSVs; missing benchmark/risk-free observations; rank/constraint changes; no-key optional failure; evidence/memo immutability; reload persisted state; chart/unit labels; clean setup and documented demo.

## Finance usability update

Touches import parsing, preview/commit API contracts, additive upload provenance migration, suitability serialization, upload/shortlist/memo UI, and Excel/Word exports. Financial formulas, hard gates, ranking weights, and existing evidence snapshots retain their semantics. Existing CSV upload API remains compatible. Optional export failure cannot erase a saved evaluation. No live AI changes or new credential provisioning.

Verification covers nonmutating previews, corrections and original-file preservation, duplicate/conflicting imports, XLSX formats/formulas/worksheet selection, export values and injection protection, memo ownership, suitability, TypeScript/lint/build, migrations, browser interaction, and export layout.
