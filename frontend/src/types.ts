export type Metrics = {
  observation_count: number;
  period_start: string;
  period_end: string;
  contiguous: boolean;
  annualized_return: number | null;
  cumulative_return: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  maximum_drawdown: number | null;
  calmar_ratio: number | null;
  benchmark_correlation: number | null;
  beta: number | null;
  alpha: number | null;
  tracking_error: number | null;
  information_ratio: number | null;
  upside_capture: number | null;
  downside_capture: number | null;
  excess_return: number | null;
  best_month: number | null;
  worst_month: number | null;
  positive_month_pct: number | null;
  skew: number | null;
  kurtosis: number | null;
  factor_r_squared: number | null;
  factor_alpha: number | null;
  benchmark_observation_count: number;
  risk_free_observation_count: number;
  rolling_correlation: { period: string; value: number | null }[];
};
export type Mandate = {
  name: string;
  benchmark: string;
  profile: string;
  target_volatility: number;
  maximum_volatility: number | null;
  maximum_drawdown: number;
  minimum_track_record_months: number;
  maximum_benchmark_correlation: number;
  liquidity_requirement: string;
  preferred_strategies: string[];
  excluded_strategies: string[];
  weights: Record<string, number> | null;
};
export type Fund = {
  id: string;
  canonical_name: string;
  manager_name: string;
  strategy: string;
  liquidity: string;
  management_fee: number | null;
  performance_fee: number | null;
  qualitative_notes: string;
  source_file: string;
  source_row: number;
  metrics: Metrics;
  factors: {
    betas: Record<string, number>;
    t_stats: Record<string, number | null>;
    r_squared: number | null;
    alpha: number | null;
    observations: number;
    period: string;
    status: string;
  };
  charts: {
    period: string;
    fund: number | null;
    benchmark: number | null;
    drawdown: number | null;
  }[];
  regimes: Record<
    string,
    { average_return: number | null; observations: number; periods: string[] }
  >;
  diversification: Record<string, number | null>;
  eligible: boolean;
  failed_constraints: {
    constraint: string;
    actual: unknown;
    limit: unknown;
    reason: string;
  }[];
  component_scores: Record<
    string,
    { score: number; weight: number; contribution: number }
  >;
  total_score: number | null;
  rank: number | null;
  evidence_ids: Record<string, string>;
  decision_evidence: string;
  data_quality_flags: number;
  synthetic: boolean;
  preference_bonus: number;
  suitability?: {
    headline: string;
    strengths: { text: string; evidence_ids: string[] }[];
    concerns: { text: string; evidence_ids: string[] }[];
    missing_evidence: string[];
    next_step: string;
  };
};
export type Lineage = {
  provider: string;
  identifier: string;
  retrieved_at: string;
  live_or_cached: string;
  synthetic: boolean;
  transformation: string;
  fallback_reason?: string;
};
export type Run = {
  run_id: string;
  mandate: Mandate;
  mandate_evidence: string;
  weights: Record<string, number>;
  funds: Fund[];
  changes: {
    fund_id: string;
    fund: string;
    from_rank: number | null;
    to_rank: number | null;
    from_eligible: boolean;
    to_eligible: boolean;
    reasons: string[];
  }[];
  sources: Record<string, Lineage>;
  market_status: string;
  created_at: string;
};
export type Evidence = {
  id: string;
  type: string;
  label: string;
  value: { value: unknown };
  unit: string;
  source: string;
  observation_period: string;
  live_or_cached: string;
  methodology?: string;
  source_identifier?: string;
  provenance?: Record<string, unknown>;
};
export type Claim = {
  id?: string;
  text: string;
  claim_type: string;
  confidence: string;
  evidence_ids: string[];
  fund_id?: string;
};
export type Memo = {
  id: string;
  run_id: string;
  kind: string;
  generated_at: string;
  payload: {
    recommended_fund_id?: string;
    sections: { title: string; claims: Claim[] }[];
  };
  model_metadata: Record<string, unknown>;
  claims: Claim[];
};
export type Issue = {
  id: string;
  severity: string;
  issue_type: string;
  fund_id: string | null;
  source_file: string;
  source_row: number | null;
  description: string;
  inferred_resolution: string | null;
  status: string;
};
export type Health = {
  uploads: {
    total_rows: number;
    valid_rows: number;
    warnings: number;
    errors: number;
    normalization_actions: number;
    funds_affected: number;
    filename: string;
    upload_id: string;
  }[];
  categories: Record<string, number>;
  issues: Issue[];
};
