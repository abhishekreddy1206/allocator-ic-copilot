
CREATE TABLE benchmark_returns (
	id VARCHAR NOT NULL,
	symbol VARCHAR NOT NULL,
	period VARCHAR(7) NOT NULL,
	return_value FLOAT NOT NULL,
	lineage JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (symbol, period)
)

;

CREATE TABLE factor_returns (
	id VARCHAR NOT NULL,
	factor VARCHAR NOT NULL,
	period VARCHAR(7) NOT NULL,
	return_value FLOAT NOT NULL,
	lineage JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (factor, period)
)

;

CREATE TABLE macro_observations (
	id VARCHAR NOT NULL,
	series_id VARCHAR NOT NULL,
	period VARCHAR(7) NOT NULL,
	value FLOAT NOT NULL,
	lineage JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (series_id, period)
)

;

CREATE TABLE mandates (
	id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	parameters JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE uploads (
	id VARCHAR NOT NULL,
	filename VARCHAR NOT NULL,
	sha256 VARCHAR NOT NULL,
	raw_csv TEXT NOT NULL,
	summary JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (sha256)
)

;

CREATE TABLE funds (
	id VARCHAR NOT NULL,
	canonical_name VARCHAR NOT NULL,
	external_identifier VARCHAR NOT NULL,
	manager_name VARCHAR NOT NULL,
	strategy VARCHAR NOT NULL,
	liquidity VARCHAR NOT NULL,
	management_fee FLOAT,
	performance_fee FLOAT,
	qualitative_notes TEXT NOT NULL,
	source_file VARCHAR NOT NULL,
	source_row INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (external_identifier),
	FOREIGN KEY(source_file) REFERENCES uploads (id)
)

;

CREATE TABLE runs (
	id VARCHAR NOT NULL,
	mandate_id VARCHAR NOT NULL,
	result JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(mandate_id) REFERENCES mandates (id)
)

;

CREATE TABLE data_quality_issues (
	id VARCHAR NOT NULL,
	severity VARCHAR NOT NULL,
	issue_type VARCHAR NOT NULL,
	fund_id VARCHAR,
	source_file VARCHAR NOT NULL,
	source_row INTEGER,
	description TEXT NOT NULL,
	inferred_resolution TEXT,
	status VARCHAR NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(fund_id) REFERENCES funds (id),
	FOREIGN KEY(source_file) REFERENCES uploads (id)
)

;

CREATE TABLE evaluations (
	id VARCHAR NOT NULL,
	fund_id VARCHAR NOT NULL,
	mandate_id VARCHAR NOT NULL,
	run_id VARCHAR NOT NULL,
	eligible BOOLEAN NOT NULL,
	failed_constraints JSONB NOT NULL,
	component_scores JSONB NOT NULL,
	total_score FLOAT,
	rank INTEGER,
	PRIMARY KEY (id),
	UNIQUE (fund_id, run_id),
	FOREIGN KEY(fund_id) REFERENCES funds (id),
	FOREIGN KEY(mandate_id) REFERENCES mandates (id),
	FOREIGN KEY(run_id) REFERENCES runs (id)
)

;

CREATE TABLE evidence (
	id VARCHAR NOT NULL,
	run_id VARCHAR NOT NULL,
	type VARCHAR NOT NULL,
	label VARCHAR NOT NULL,
	value JSONB NOT NULL,
	unit VARCHAR NOT NULL,
	source VARCHAR NOT NULL,
	source_identifier VARCHAR NOT NULL,
	observation_period VARCHAR NOT NULL,
	methodology TEXT NOT NULL,
	provenance JSONB NOT NULL,
	live_or_cached VARCHAR NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(run_id) REFERENCES runs (id)
)

;

CREATE TABLE factor_exposures (
	id VARCHAR NOT NULL,
	fund_id VARCHAR NOT NULL,
	run_id VARCHAR NOT NULL,
	factor_name VARCHAR NOT NULL,
	beta FLOAT NOT NULL,
	t_stat FLOAT,
	methodology_metadata JSONB NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(fund_id) REFERENCES funds (id),
	FOREIGN KEY(run_id) REFERENCES runs (id)
)

;

CREATE TABLE memos (
	id VARCHAR NOT NULL,
	run_id VARCHAR NOT NULL,
	mandate_id VARCHAR NOT NULL,
	kind VARCHAR NOT NULL,
	recommendation VARCHAR,
	structured_sections JSONB NOT NULL,
	model_metadata JSONB NOT NULL,
	generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(run_id) REFERENCES runs (id),
	FOREIGN KEY(mandate_id) REFERENCES mandates (id)
)

;

CREATE TABLE metric_snapshots (
	id VARCHAR NOT NULL,
	fund_id VARCHAR NOT NULL,
	run_id VARCHAR NOT NULL,
	evaluation_period VARCHAR NOT NULL,
	observation_count INTEGER NOT NULL,
	metrics JSONB NOT NULL,
	methodology JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (fund_id, run_id),
	FOREIGN KEY(fund_id) REFERENCES funds (id),
	FOREIGN KEY(run_id) REFERENCES runs (id)
)

;

CREATE TABLE monthly_returns (
	id VARCHAR NOT NULL,
	fund_id VARCHAR NOT NULL,
	period VARCHAR(7) NOT NULL,
	return_value FLOAT NOT NULL,
	source_file VARCHAR NOT NULL,
	source_row INTEGER NOT NULL,
	normalization_metadata JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (fund_id, period),
	FOREIGN KEY(fund_id) REFERENCES funds (id),
	FOREIGN KEY(source_file) REFERENCES uploads (id)
)

;

CREATE TABLE memo_claims (
	id VARCHAR NOT NULL,
	memo_id VARCHAR NOT NULL,
	text TEXT NOT NULL,
	claim_type VARCHAR NOT NULL,
	confidence VARCHAR NOT NULL,
	evidence_ids JSONB NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(memo_id) REFERENCES memos (id)
)

;
CREATE INDEX ix_benchmark_returns_symbol ON benchmark_returns (symbol);
CREATE INDEX ix_funds_strategy ON funds (strategy);
CREATE INDEX ix_data_quality_issues_issue_type ON data_quality_issues (issue_type);
CREATE INDEX ix_evaluations_run_id ON evaluations (run_id);
CREATE INDEX ix_evidence_run_id ON evidence (run_id);
CREATE INDEX ix_evidence_type ON evidence (type);
CREATE INDEX ix_memos_run_id ON memos (run_id);
CREATE INDEX ix_metric_snapshots_run_id ON metric_snapshots (run_id);
CREATE INDEX ix_monthly_returns_fund_id ON monthly_returns (fund_id);
CREATE INDEX ix_monthly_returns_period ON monthly_returns (period);
CREATE INDEX ix_memo_claims_memo_id ON memo_claims (memo_id);
