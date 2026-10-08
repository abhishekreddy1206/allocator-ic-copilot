# Allocator IC Copilot

An internal allocator decision prototype. Deterministic software owns facts. AI helps interpret them. No Equi branding or implied affiliation.

## Primary journey
Load a clearly synthetic 18-manager universe; inspect normalization and rejected rows; evaluate a Diversifier mandate; tighten drawdown from 15% to 7%, then quarterly liquidity to monthly; inspect deterministic changes and evidence; open a rules-based briefing; optionally request an evidence-bound AI memo and challenge.

## Contracts and scope
Monthly CSV rows have fund_id, fund_name, manager_name, strategy, liquidity, management_fee, performance_fee, period, monthly_return, qualitative_notes. Explicit percent strings and bare decimal returns are supported; ambiguous bare percentage-point returns are rejected. Missing months are never imputed. Conflicting identifiers are quarantined. Metrics use decimals at every backend boundary. Liquidity is an ordinal frequency, not a claim about gates or settlement terms.

P0: PostgreSQL/Alembic, ingestion, deterministic finance, market providers/fallbacks, persisted mandate/ranking, Data Health, Universe, Decision Room, tests, reproducible setup.
P1: evidence, factor regression, diversification, optional structured AI memo/challenge, claim audit.
Out of scope: authentication, allocation optimization, institutional feeds, production deployment, trading and forecasts.

## Acceptance
No key is required. No fallback may be labeled live. Rankings exclude hard failures. Every evaluation is immutable and evidence keys are evaluation-scoped. A changed mandate cannot silently reuse an old memo. The five-minute flow must work offline and have executable integration coverage.
