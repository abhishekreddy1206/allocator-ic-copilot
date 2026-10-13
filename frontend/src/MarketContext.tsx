import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api, num, pct } from "./api";

type Context = {
  benchmark: string;
  period: string | null;
  status: string;
  chart: { period: string; index: number | null }[];
  metrics: {
    return_3m: number | null;
    return_12m: number | null;
    volatility_12m: number | null;
  };
  indicators: {
    identifier: string;
    title: string;
    unit: string;
    value: number | null;
    period: string | null;
    change: number | null;
    source: string | null;
    status: string | null;
    evidence_id: string | null;
    previous_evidence_id: string | null;
  }[];
  observations: {
    id: string;
    period: string;
    value: number | null;
    source: string;
    status: string;
  }[];
  methodology: string;
};

export default function MarketContext({
  runId,
  openEvidence,
}: {
  runId: string;
  openEvidence: (id: string) => Promise<void>;
}) {
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let live = true;
    setContext(null);
    setError("");
    api<Context>(`/runs/${runId}/market-context`)
      .then((result) => {
        if (live) setContext(result);
      })
      .catch((e: Error) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [runId, retry]);
  return (
    <section className="panel market-context" aria-label="Market trends">
      <div className="panel-title">
        <div>
          <h2>Market trends</h2>
          <p>
            {context
              ? `${context.benchmark} benchmark · Monthly observations through ${context.period || "unavailable"}`
              : "Market context for this saved evaluation"}
          </p>
        </div>
        {context && (
          <span
            className={`source-badge ${context.status.includes("CACHED") || context.status.includes("MIXED") ? "demo-source" : "live-source"}`}
          >
            {context.status}
          </span>
        )}
      </div>
      {!context && !error && (
        <p className="footnote" role="status">
          Loading market history…
        </p>
      )}
      {error && (
        <div className="market-error" role="alert">
          <p>Market history could not load: {error}</p>
          <button className="button small" onClick={() => setRetry(retry + 1)}>
            Retry market history
          </button>
        </div>
      )}
      {context && (
        <>
          <div className="market-overview">
            <div>
              <h3>Recent benchmark history · growth of 100</h3>
              <div className="market-chart">
                {context.chart.length ? (
                  <ResponsiveContainer>
                    <LineChart
                      data={context.chart}
                      margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="#e5ebe5"
                      />
                      <XAxis
                        dataKey="period"
                        minTickGap={35}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        domain={["auto", "auto"]}
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: number) => num(v, 0)}
                        width={44}
                      />
                      <Tooltip
                        formatter={(value) => [
                          typeof value === "number"
                            ? num(value, 2)
                            : String(value),
                          "Index",
                        ]}
                      />
                      <Line
                        type="linear"
                        dataKey="index"
                        stroke="#2c7464"
                        strokeWidth={2.5}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="empty">
                    Chart unavailable: monthly coverage is missing or invalid.
                  </p>
                )}
              </div>
            </div>
            <div className="market-metrics">
              {(
                [
                  ["3-month return", context.metrics.return_3m],
                  ["12-month return", context.metrics.return_12m],
                  [
                    "Annualized volatility · 12 months",
                    context.metrics.volatility_12m,
                  ],
                ] as const
              ).map(([title, value]) => (
                <div key={title}>
                  <span>{title}</span>
                  <strong>{pct(value)}</strong>
                  {value == null && (
                    <small>Complete monthly history required</small>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="market-indicators">
            {context.indicators.map((indicator) => (
              <div key={indicator.identifier}>
                <h3>{indicator.title}</h3>
                <strong>
                  {num(indicator.value)} <small>{indicator.unit}</small>
                </strong>
                <p>
                  {indicator.period
                    ? `As of ${indicator.period}`
                    : "No observation available"}{" "}
                  ·{" "}
                  {indicator.status === "live"
                    ? "Live source"
                    : indicator.status === "cached"
                      ? "Synthetic demo"
                      : "Unavailable"}
                </p>
                {indicator.change != null && (
                  <p>
                    Month-on-month: {indicator.change > 0 ? "+" : ""}
                    {num(indicator.change)}{" "}
                    {indicator.unit === "% yield"
                      ? "percentage points"
                      : "index points"}
                  </p>
                )}
                <div>
                  {indicator.evidence_id && (
                    <button
                      className="text-link"
                      onClick={() => void openEvidence(indicator.evidence_id!)}
                    >
                      Source observation
                    </button>
                  )}
                  {indicator.previous_evidence_id && (
                    <button
                      className="text-link"
                      onClick={() =>
                        void openEvidence(indicator.previous_evidence_id!)
                      }
                    >
                      Prior month
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <details className="market-methods review-details">
            <summary>Methods & benchmark source observations</summary>
            <p>{context.methodology}</p>
            <div className="market-source-list">
              {context.observations.map((row) => (
                <button
                  className="button small"
                  key={row.id}
                  onClick={() => void openEvidence(row.id)}
                >
                  {row.period} · {pct(row.value)} ·{" "}
                  {row.status === "live" ? "Live" : "Demo"}
                </button>
              ))}
            </div>
          </details>
          <p className="footnote">
            Historical context from this evaluation, not real-time quotes. Use
            Refresh public data below to retrieve newer observations.
          </p>
        </>
      )}
    </section>
  );
}
