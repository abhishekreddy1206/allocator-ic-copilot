import { useState, useEffect, useRef, useCallback } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  ChevronRight,
  Database,
  FileText,
  Layers,
  LayoutDashboard,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  Users,
  X,
  RefreshCw,
  AlertTriangle,
  Scale,
  Bookmark,
  ExternalLink,
  Download,
} from "lucide-react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ReferenceLine,
} from "recharts";
import { api, post, pct, num, label } from "./api";
import type {
  Run,
  Fund,
  Mandate,
  Health,
  Evidence,
  Memo,
  Claim,
} from "./types";

const pages = [
  "Overview",
  "Data Health",
  "Universe",
  "Decision Room",
  "Shortlist",
  "IC Memo",
  "Audit",
] as const;
type Page = (typeof pages)[number];
const icons = [
  LayoutDashboard,
  ShieldCheck,
  Users,
  SlidersHorizontal,
  Bookmark,
  FileText,
  Database,
];
const strategies = [
  "Global Macro",
  "CTA / Managed Futures",
  "Equity Long/Short",
  "Relative Value",
  "Credit",
  "Multi-Strategy",
  "Event Driven",
  "Market Neutral",
];
function Status({ eligible }: { eligible: boolean }) {
  return (
    <span className={`pill ${eligible ? "eligible" : "excluded"}`}>
      {eligible ? <Check size={11} /> : <X size={11} />}{" "}
      {eligible ? "Eligible" : "Ineligible"}
    </span>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <Layers size={30} />
      <p>{text}</p>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("Overview"),
    [run, setRun] = useState<Run | null>(null),
    [draft, setDraft] = useState<Mandate | null>(null),
    [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [ai, setAI] = useState(false);
  const [selected, setSelected] = useState<Fund | null>(null),
    [evidence, setEvidence] = useState<Evidence | null>(null),
    [memo, setMemo] = useState<Memo | null>(null),
    [challenge, setChallenge] = useState<Memo | null>(null);
  const [search, setSearch] = useState(""),
    [strategy, setStrategy] = useState("All strategies"),
    [sort, setSort] = useState("rank"),
    [issueFilter, setIssueFilter] = useState("all"),
    [issuePage, setIssuePage] = useState(0),
    [auditType, setAuditType] = useState(""),
    [auditSearch, setAuditSearch] = useState(""),
    [auditRows, setAuditRows] = useState<Evidence[]>([]);
  const filteredIssues =
    health?.issues.filter(
      (i) =>
        issueFilter === "all" ||
        i.severity === issueFilter ||
        i.issue_type === issueFilter,
    ) || [];
  const changeIssueFilter = (value: string) => {
    setIssueFilter(value);
    setIssuePage(0);
  };
  const current = useRef<Run | null>(null),
    committed = useRef(""),
    requestId = useRef(0);
  const accept = useCallback((r: Run) => {
    current.current = r;
    committed.current = JSON.stringify(r.mandate);
    setRun(r);
    setDraft(r.mandate);
    setMemo(null);
    setChallenge(null);
    setSelected((prev) =>
      prev ? r.funds.find((f) => f.id === prev.id) || null : null,
    );
  }, []);
  useEffect(() => {
    Promise.all([
      api<Run | null>("/runs/latest"),
      api<{ ai_available: boolean }>("/config"),
      api<Health>("/data-health"),
    ])
      .then(([r, c, h]) => {
        if (r) accept(r);
        setAI(c.ai_available);
        setHealth(h);
      })
      .catch((e) => setError(String(e.message)))
      .finally(() => setLoading(false));
  }, [accept]);
  useEffect(() => {
    if (!draft || JSON.stringify(draft) === committed.current) return;
    const id = ++requestId.current;
    setBusy("Evaluating mandate");
    const timer = setTimeout(() => {
      post<Run>("/evaluations", {
        mandate: draft,
        previous_run_id: current.current?.run_id,
      })
        .then((r) => {
          if (id === requestId.current) {
            accept(r);
            setError("");
          }
        })
        .catch((e) => {
          if (id === requestId.current) setError(e.message);
        })
        .finally(() => {
          if (id === requestId.current) setBusy("");
        });
    }, 550);
    return () => clearTimeout(timer);
  }, [draft, accept]);
  useEffect(() => {
    if (!run) return;
    let live = true;
    api<Memo[]>(`/memos?run_id=${run.run_id}`)
      .then((rows) => {
        if (live) {
          setMemo(rows.find((m) => m.kind !== "challenge") || null);
          setChallenge(rows.find((m) => m.kind === "challenge") || null);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [run]);
  useEffect(() => {
    if (!run || page !== "Audit") return;
    let live = true;
    const timer = setTimeout(() => {
      api<Evidence[]>(
        `/evidence?run_id=${run.run_id}&type=${auditType}&q=${encodeURIComponent(auditSearch)}&limit=500`,
      )
        .then((rows) => {
          if (live) setAuditRows(rows);
        })
        .catch((e) => {
          if (live) setError(e.message);
        });
    }, 200);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [run, page, auditType, auditSearch]);
  const openEvidence = async (id: string) => {
    try {
      setEvidence(await api<Evidence>(`/evidence/${encodeURIComponent(id)}`));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  async function action(name: string, fn: () => Promise<void>) {
    setBusy(name);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function seed() {
    await action("Loading demo", async () => {
      const r = await post<{ result: Run }>("/demo", {});
      accept(r.result);
      setHealth(await api<Health>("/data-health"));
      setNotice(
        "Synthetic demo loaded with cached market fixtures. Original uploads and past evaluations are preserved.",
      );
    });
  }
  async function upload(files: FileList | null) {
    if (!files?.length) return;
    await action("Validating CSVs", async () => {
      const body = new FormData();
      Array.from(files).forEach((f) => body.append("files", f));
      const r = await api<{ result: Run }>("/uploads", {
        method: "POST",
        body,
      });
      accept(r.result);
      setHealth(await api<Health>("/data-health"));
      setPage("Data Health");
      setNotice(
        "Upload processed. Inspect rejected rows and normalization actions below.",
      );
    });
  }
  async function generate(kind: string) {
    if (!run) return;
    await action(
      kind === "briefing"
        ? "Preparing briefing"
        : "Generating verified AI interpretation",
      async () => {
        const m = await post<Memo>("/memos", { run_id: run.run_id, kind });
        if (kind === "challenge") setChallenge(m);
        else setMemo(m);
      },
    );
  }
  const eligible = run?.funds.filter((f) => f.eligible) || [],
    top = eligible.slice(0, 5);
  const navigate = (p: Page) => {
    window.scrollTo({ top: 0, behavior: "auto" });
    setPage(p);
    setSearch("");
  };
  const evidenceButtons = (claim: Claim) => (
    <span className="evidence-links">
      {claim.evidence_ids.map((id, i) => (
        <button key={id} onClick={() => openEvidence(id)} title={id}>
          <Database size={11} /> {i + 1}
        </button>
      ))}
    </span>
  );
  const renderMemo = (m: Memo) => (
    <article className="memo-paper">
      <div className="memo-letterhead">
        <span>ALLOCATOR / INVESTMENT COMMITTEE</span>
        <span>
          {m.kind === "briefing"
            ? "RULES-BASED BRIEFING"
            : "AI-ASSISTED INTERPRETATION"}
        </span>
      </div>
      <h2>
        {m.kind === "challenge"
          ? "Challenge the recommendation"
          : "Investment committee memorandum"}
      </h2>
      <div className="memo-meta">
        {new Date(m.generated_at).toLocaleDateString()} · Run{" "}
        {m.run_id.slice(0, 8)} · {String(m.model_metadata.provider)}
      </div>
      {m.payload.sections.map((s, i) => (
        <section key={i}>
          <h3>{s.title}</h3>
          {s.claims.map((c, j) => (
            <p key={j}>
              {c.fund_id && (
                <strong>
                  {run?.funds.find((f) => f.id === c.fund_id)?.canonical_name}{" "}
                  ·{" "}
                </strong>
              )}
              {c.text} {evidenceButtons(c)}
              {m.kind !== "briefing" && (
                <small className="confidence">
                  {c.claim_type} / {c.confidence} confidence
                </small>
              )}
            </p>
          ))}
        </section>
      ))}
      <footer>
        Verified calculations support the decision; interpretations require
        investment-team judgment. Synthetic manager histories are not investable
        performance.
      </footer>
    </article>
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Layers size={23} />
          </div>
          <div>
            ALLOCATOR<span>IC COPILOT</span>
          </div>
        </div>
        <div className="workspace-label">
          RESEARCH WORKSPACE <span>01</span>
        </div>
        <nav>
          {pages.map((p, i) => {
            const Icon = icons[i];
            return (
              <button
                key={p}
                aria-label={p}
                onClick={() => navigate(p)}
                className={page === p ? "active" : ""}
              >
                <Icon size={18} />
                <span>{p}</span>
                {p === "Decision Room" && <span className="nav-dot" />}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="principle">
            <Scale size={18} />
            <p>
              Deterministic software owns facts.
              <br />
              <span>AI helps interpret them.</span>
            </p>
          </div>
          <div className="profile">
            <div className="avatar">IC</div>
            <div>
              Investment research
              <span>Internal prototype · Synthetic demo</span>
            </div>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            Research workspace <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div>
            <span className="connection">
              <span /> Evidence connected
            </span>
            <label className={`button small ${busy ? "disabled" : ""}`}>
              <Upload size={14} /> Import CSV
              <input
                type="file"
                accept=".csv"
                multiple
                disabled={!!busy}
                onChange={(e) => {
                  void upload(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </div>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">INVESTMENT DECISION INTELLIGENCE</div>
              <h1>
                {page === "Overview" ? "Clarity before conviction." : page}
              </h1>
              <p>
                {page === "Overview"
                  ? "From manager data to a defensible investment decision."
                  : page === "Decision Room"
                    ? "Change the mandate. See the decision move. Every change has a reason."
                    : page === "Data Health"
                      ? "Inspect what changed, what was rejected, and what remains unresolved."
                      : page === "Audit"
                        ? "Trace each claim through verified evidence to its source and methodology."
                        : page === "IC Memo"
                          ? "A committee-ready narrative, grounded in an immutable evaluation."
                          : "Verified performance. Explicit constraints. Transparent comparisons."}
              </p>
            </div>
            <div className="heading-actions">
              {run && (
                <span className="source-badge">
                  <span /> {run.market_status}
                </span>
              )}
              <button
                className="button ghost small"
                disabled={!!busy}
                onClick={seed}
              >
                <RefreshCw size={14} /> Load demo
              </button>
            </div>
          </div>
          {error && (
            <div role="alert" className="banner error">
              <AlertTriangle size={16} />
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="banner">
              <Check size={16} />
              {notice}
              <button onClick={() => setNotice("")} aria-label="Dismiss notice">
                <X size={16} />
              </button>
            </div>
          )}
          {busy && (
            <div role="status" className="working">
              <RefreshCw size={14} className="spin" />
              {busy}…
              {busy === "Evaluating mandate"
                ? " Showing the last completed evaluation until the new run is ready."
                : ""}
            </div>
          )}
          {loading ? (
            <Empty text="Connecting to the research workspace…" />
          ) : !run ? (
            <div className="panel">
              <Empty text="Start with the intentionally messy synthetic manager universe." />
              <button className="button primary" onClick={seed}>
                Load synthetic demo <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            <>
              {page === "Overview" && (
                <>
                  <div className="stats">
                    <Stat
                      title="MANAGER UNIVERSE"
                      value={String(run.funds.length)}
                      subtitle="Across eight alternative strategies"
                      icon={<Users size={18} />}
                    />
                    <Stat
                      title="MANDATE ELIGIBLE"
                      value={String(eligible.length)}
                      subtitle={`${run.funds.length - eligible.length} excluded by hard constraints`}
                      icon={<ShieldCheck size={18} />}
                    />
                    <Stat
                      title="DATA COVERAGE"
                      value={`${Math.max(...run.funds.map((f) => f.metrics.observation_count))} months`}
                      subtitle="Gaps and incomplete history flagged"
                      icon={<Database size={18} />}
                    />
                    <Stat
                      title="CURRENT MANDATE"
                      value={run.mandate.profile}
                      subtitle={`${run.mandate.benchmark} · ${run.mandate.liquidity_requirement} liquidity`}
                      icon={<SlidersHorizontal size={18} />}
                    />
                  </div>
                  <div className="overview-grid">
                    <div className="panel">
                      <div className="panel-title">
                        <div>
                          <h2>The opportunity set</h2>
                          <p>
                            Observed risk and return · selected benchmark{" "}
                            {run.mandate.benchmark}
                          </p>
                        </div>
                        <span className="tiny-label">MONTHLY RETURNS</span>
                      </div>
                      <RiskChart funds={run.funds} />
                      <div className="chart-legend">
                        <span>
                          <i className="green" /> Eligible managers
                        </span>
                        <span>
                          <i className="gray" /> Ineligible managers
                        </span>
                      </div>
                    </div>
                    <div className="panel candidates">
                      <div className="panel-title">
                        <div>
                          <h2>Leading candidates</h2>
                          <p>{run.mandate.profile} mandate</p>
                        </div>
                        <Bookmark size={18} />
                      </div>
                      {top.slice(0, 3).map((f) => (
                        <button
                          className="candidate"
                          key={f.id}
                          onClick={() => setSelected(f)}
                        >
                          <span className="candidate-rank">
                            {String(f.rank).padStart(2, "0")}
                          </span>
                          <div>
                            <strong>{f.canonical_name}</strong>
                            <span>{f.strategy}</span>
                            <small>
                              {pct(f.metrics.annualized_return)} return <b>·</b>{" "}
                              {num(f.metrics.sharpe_ratio)} Sharpe
                            </small>
                          </div>
                          <div className="score">
                            {num(f.total_score, 1)}
                            <small>/ 100</small>
                          </div>
                        </button>
                      ))}
                      {!top.length && (
                        <Empty text="No manager passes this mandate." />
                      )}
                      <button
                        className="text-link"
                        onClick={() => navigate("Decision Room")}
                      >
                        Enter Decision Room <ArrowUpRight size={16} />
                      </button>
                    </div>
                  </div>
                  <div className="bottom-grid">
                    <div className="panel data-health-card">
                      <div className="panel-title">
                        <div>
                          <h2>Data deserves scrutiny</h2>
                          <p>
                            Messy input is a first-class part of the decision.
                          </p>
                        </div>
                        <ShieldCheck size={19} />
                      </div>
                      <div className="health-inline">
                        <div>
                          <strong>
                            {health?.uploads.reduce(
                              (n, u) => n + u.valid_rows,
                              0,
                            )}
                          </strong>
                          <span>accepted observations</span>
                        </div>
                        <div>
                          <strong className="amber-text">
                            {health?.uploads.reduce(
                              (n, u) => n + u.warnings,
                              0,
                            )}
                          </strong>
                          <span>warnings to review</span>
                        </div>
                        <div>
                          <strong>
                            {health?.uploads.reduce(
                              (n, u) => n + u.normalization_actions,
                              0,
                            )}
                          </strong>
                          <span>logged transformations</span>
                        </div>
                      </div>
                      <button
                        className="text-link"
                        onClick={() => navigate("Data Health")}
                      >
                        Inspect data health <ArrowRight size={15} />
                      </button>
                    </div>
                    <div className="decision-callout">
                      <div className="eyebrow">THE MANDATE IS THE LENS</div>
                      <h2>
                        A better manager.
                        <br />
                        For which portfolio?
                      </h2>
                      <p>
                        Tighten drawdown tolerance or liquidity requirements.
                        Watch eligibility and the shortlist change.
                      </p>
                      <button
                        className="button light"
                        onClick={() => navigate("Decision Room")}
                      >
                        Test a decision <ArrowUpRight size={15} />
                      </button>
                    </div>
                  </div>
                  <Sources
                    run={run}
                    refresh={() =>
                      action(
                        "Refreshing public sources (fallbacks remain available)",
                        async () => {
                          const r = await post<{ result: Run }>(
                            "/market/refresh",
                            {},
                          );
                          accept(r.result);
                          setNotice(
                            "Sources refreshed. Each provider shows its actual live or cached status.",
                          );
                        },
                      )
                    }
                    busy={!!busy}
                  />
                </>
              )}
              {page === "Data Health" && health && (
                <>
                  <div className="stats">
                    {[
                      ["TOTAL ROWS", "total_rows"],
                      ["VALID ROWS", "valid_rows"],
                      ["WARNINGS", "warnings"],
                      ["ERRORS / QUARANTINED", "errors"],
                    ].map(([t, k]) => (
                      <Stat
                        key={k}
                        title={t}
                        value={String(
                          health.uploads.reduce(
                            (n, u) => n + (u[k as keyof typeof u] as number),
                            0,
                          ),
                        )}
                        subtitle="All imported source files"
                      />
                    ))}
                  </div>
                  <div className="panel">
                    <div className="panel-title">
                      <div>
                        <h2>Ingestion ledger</h2>
                        <p>
                          Original CSVs retained with SHA-256. Duplicates never
                          double-count returns.
                        </p>
                      </div>
                      <a className="button small" href="/api/demo.csv">
                        <Download size={14} /> Sample CSV
                      </a>
                    </div>
                    <div className="category-chips">
                      {Object.entries(health.categories).map(([k, v]) => (
                        <button
                          className={issueFilter === k ? "chosen" : ""}
                          key={k}
                          onClick={() =>
                            changeIssueFilter(issueFilter === k ? "all" : k)
                          }
                        >
                          {label(k)} <b>{v}</b>
                        </button>
                      ))}
                    </div>
                    <div className="filters">
                      <select
                        aria-label="Issue severity"
                        value={issueFilter}
                        onChange={(e) => changeIssueFilter(e.target.value)}
                      >
                        <option value="all">All issues and actions</option>
                        <option value="error">Errors</option>
                        <option value="warning">Warnings</option>
                        <option value="info">Normalization actions</option>
                        {Object.keys(health.categories).map((c) => (
                          <option key={c}>{c}</option>
                        ))}
                      </select>
                      <span className="muted">
                        {health.issues.length} recorded events ·{" "}
                        {
                          new Set(
                            health.issues.map((i) => i.fund_id).filter(Boolean),
                          ).size
                        }{" "}
                        funds affected · normalization actions are resolved
                      </span>
                    </div>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Severity</th>
                            <th>Category / source</th>
                            <th>What happened</th>
                            <th>Resolution</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredIssues
                            .slice(issuePage * 100, (issuePage + 1) * 100)
                            .map((i) => (
                              <tr key={i.id}>
                                <td>
                                  <span className={`pill ${i.severity}`}>
                                    {i.severity}
                                  </span>
                                </td>
                                <td>
                                  <strong>{label(i.issue_type)}</strong>
                                  <small>
                                    {
                                      health.uploads.find(
                                        (u) => u.upload_id === i.source_file,
                                      )?.filename
                                    }{" "}
                                    · {i.fund_id || "File"} ·{" "}
                                    {i.source_row
                                      ? `row ${i.source_row}`
                                      : "history check"}
                                  </small>
                                </td>
                                <td className="issue-description">
                                  {i.description}
                                </td>
                                <td>
                                  <small>
                                    {i.inferred_resolution || "Requires review"}
                                  </small>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="footnote">
                      Page {issuePage + 1} of{" "}
                      {Math.max(1, Math.ceil(filteredIssues.length / 100))} ·{" "}
                      {filteredIssues.length} matching events.
                      <button
                        className="button small"
                        disabled={issuePage === 0}
                        onClick={() => setIssuePage(issuePage - 1)}
                      >
                        Previous
                      </button>
                      <button
                        className="button small"
                        disabled={
                          (issuePage + 1) * 100 >= filteredIssues.length
                        }
                        onClick={() => setIssuePage(issuePage + 1)}
                      >
                        Next
                      </button>
                    </p>
                  </div>
                </>
              )}
              {page === "Universe" && (
                <div className="panel">
                  <div className="panel-title">
                    <div>
                      <h2>
                        Manager universe{" "}
                        <span className="count">{run.funds.length}</span>
                      </h2>
                      <p>
                        Click a manager to inspect performance, factors, source
                        notes and evidence.
                      </p>
                    </div>
                    <span className="tiny-label">
                      SYNTHETIC DEMO MANAGERS MARKED
                    </span>
                  </div>
                  <div className="filters">
                    <div className="search">
                      <Search size={15} />
                      <input
                        aria-label="Search managers"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search managers or strategies…"
                      />
                    </div>
                    <select
                      aria-label="Filter strategy"
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                    >
                      <option>All strategies</option>
                      {strategies.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                    <select
                      aria-label="Sort managers"
                      value={sort}
                      onChange={(e) => setSort(e.target.value)}
                    >
                      <option value="rank">Sort by rank</option>
                      <option value="annualized_return">Sort by return</option>
                      <option value="sharpe_ratio">Sort by Sharpe</option>
                      <option value="maximum_drawdown">Sort by drawdown</option>
                    </select>
                  </div>
                  <FundTable
                    funds={run.funds
                      .filter(
                        (f) =>
                          (strategy === "All strategies" ||
                            f.strategy === strategy) &&
                          `${f.canonical_name} ${f.strategy} ${f.manager_name}`
                            .toLowerCase()
                            .includes(search.toLowerCase()),
                      )
                      .sort((a, b) =>
                        sort === "rank"
                          ? (a.rank ?? 999) - (b.rank ?? 999)
                          : (b.metrics[sort as "annualized_return"] ?? -999) -
                            (a.metrics[sort as "annualized_return"] ?? -999),
                      )}
                    onSelect={setSelected}
                    benchmark={run.mandate.benchmark}
                  />
                </div>
              )}
              {page === "Decision Room" && draft && (
                <div className="decision-layout">
                  <div className="panel mandate-panel">
                    <div className="panel-title">
                      <div>
                        <h2>Investment mandate</h2>
                        <p>Hard gates. Soft preferences.</p>
                      </div>
                      <SlidersHorizontal size={18} />
                    </div>
                    <MandateControls mandate={draft} onChange={setDraft} />
                    <div className="method-note">
                      <ShieldCheck size={16} />
                      <p>
                        Hard constraints exclude managers before scoring.
                        Controls recompute automatically.
                      </p>
                    </div>
                    <button
                      className="button full"
                      disabled={!!busy}
                      onClick={() =>
                        setDraft({
                          ...run.mandate,
                          profile: "Diversifier",
                          benchmark: "SPY",
                          maximum_drawdown: 0.15,
                          target_volatility: 0.1,
                          maximum_volatility: 0.25,
                          minimum_track_record_months: 36,
                          liquidity_requirement: "quarterly",
                          maximum_benchmark_correlation: 0.4,
                          excluded_strategies: [],
                          weights: null,
                        })
                      }
                    >
                      Reset demo mandate
                    </button>
                  </div>
                  <div className="decision-results">
                    <div className="decision-summary">
                      <div>
                        <span className="eyebrow">CURRENT DECISION</span>
                        <h2>{eligible.length} managers pass the mandate.</h2>
                        <p>
                          {run.funds.length - eligible.length} excluded ·{" "}
                          {run.mandate.profile} priorities · Run{" "}
                          {run.run_id.slice(0, 8)}
                        </p>
                      </div>
                      <span className="pill eligible">
                        <ShieldCheck size={13} /> Deterministic
                      </span>
                    </div>
                    <div className="panel change-panel">
                      <div className="panel-title">
                        <div>
                          <h2>What changed?</h2>
                          <p>
                            Computed from this run and the previous evaluation.
                          </p>
                        </div>
                        <ArrowRight size={17} />
                      </div>
                      {run.changes.length ? (
                        run.changes.slice(0, 8).map((c) => (
                          <div className="change-row" key={c.fund_id}>
                            <div>
                              <strong>{c.fund}</strong>
                              <span
                                className={
                                  c.to_eligible ? "rank-change" : "loss-change"
                                }
                              >
                                {c.from_eligible
                                  ? `#${c.from_rank}`
                                  : "Ineligible"}{" "}
                                <ArrowRight size={12} />{" "}
                                {c.to_eligible ? `#${c.to_rank}` : "INELIGIBLE"}
                              </span>
                            </div>
                            <p>{c.reasons.join(" ")}</p>
                          </div>
                        ))
                      ) : (
                        <p className="muted">
                          Begin with a 15% drawdown limit. Tighten it to 7%,
                          then switch quarterly liquidity to monthly.
                        </p>
                      )}
                    </div>
                    <div className="panel">
                      <div className="panel-title">
                        <div>
                          <h2>Live ranking</h2>
                          <p>Only eligible managers receive a score.</p>
                        </div>
                        <span className="count">
                          {eligible.length} eligible
                        </span>
                      </div>
                      <FundTable
                        funds={run.funds}
                        compact
                        onSelect={setSelected}
                        benchmark={run.mandate.benchmark}
                      />
                    </div>
                    <div className="panel">
                      <div className="panel-title">
                        <div>
                          <h2>Ranking methodology</h2>
                          <p>
                            Fixed bounded scales · visible preference weights ·
                            decision aid
                          </p>
                        </div>
                      </div>
                      <div className="weight-grid">
                        {Object.entries(run.weights).map(([k, v]) => (
                          <div key={k}>
                            <span>{label(k)}</span>
                            <strong>{pct(v, 0)}</strong>
                          </div>
                        ))}
                      </div>
                      <p className="footnote">
                        Missing metrics earn no soft credit. Negative
                        correlation receives full correlation credit. Details
                        and score contributions are available in each manager’s
                        evidence.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {page === "Shortlist" && (
                <>
                  <div className="shortlist-grid">
                    {top.map((f) => (
                      <div className="panel shortlist-card" key={f.id}>
                        <div className="shortlist-top">
                          <span className="candidate-rank">
                            {String(f.rank).padStart(2, "0")}
                          </span>
                          <Status eligible={f.eligible} />
                        </div>
                        <h2>{f.canonical_name}</h2>
                        <p className="muted">
                          {f.strategy} · {f.liquidity}
                        </p>
                        <div className="shortlist-score">
                          <strong>{num(f.total_score, 1)}</strong>
                          <span>TRANSPARENT SCORE / 100</span>
                        </div>
                        {Object.entries(f.component_scores).map(([k, v]) => (
                          <div className="score-component" key={k}>
                            <div>
                              <span>{label(k)}</span>
                              <small>
                                {num(v.contribution, 1)} pts ·{" "}
                                {pct(v.weight, 0)} weight
                              </small>
                            </div>
                            <div className="score-track">
                              <span style={{ width: `${v.score}%` }} />
                            </div>
                          </div>
                        ))}
                        <div className="card-risk">
                          <strong>DILIGENCE PRIORITY</strong>
                          <p>{f.qualitative_notes}</p>
                        </div>
                        <button
                          className="text-link"
                          onClick={() => setSelected(f)}
                        >
                          Inspect mandate fit <ArrowUpRight size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                  {!top.length && (
                    <Empty text="No eligible managers. Revisit the mandate or data quality." />
                  )}
                </>
              )}
              {page === "IC Memo" && (
                <>
                  <div className="memo-toolbar">
                    <div>
                      <strong>{run.mandate.name}</strong>
                      <p>
                        Artifacts are tied to this evaluation. Changing the
                        mandate starts a new memo context.
                      </p>
                    </div>
                    <div>
                      <button
                        className="button"
                        disabled={!!busy}
                        onClick={() => generate("briefing")}
                      >
                        <FileText size={15} /> Rules-based briefing
                      </button>
                      <button
                        className="button primary"
                        disabled={!ai || !!busy || !eligible.length}
                        onClick={() => generate("memo")}
                      >
                        <Layers size={15} /> Generate AI memo
                      </button>
                      <button
                        className="button"
                        disabled={!ai || !!busy || !eligible.length}
                        onClick={() => generate("challenge")}
                      >
                        <Scale size={15} /> Challenge Recommendation
                      </button>
                      {memo && (
                        <button
                          className="button"
                          onClick={() => window.print()}
                        >
                          <Download size={15} /> Print / PDF
                        </button>
                      )}
                    </div>
                  </div>
                  {!ai && (
                    <div className="banner">
                      Live AI is unavailable without OPENAI_API_KEY. The
                      auditable rules-based briefing is fully available.
                    </div>
                  )}
                  {memo ? (
                    renderMemo(memo)
                  ) : (
                    <Empty text="Create a rules-based briefing or an optional evidence-bound AI memo." />
                  )}
                  {challenge && renderMemo(challenge)}
                </>
              )}
              {page === "Audit" && (
                <>
                  <div className="panel">
                    <div className="panel-title">
                      <div>
                        <h2>Evidence registry</h2>
                        <p>
                          Evaluation-scoped facts · immutable lineage · exact
                          source rows
                        </p>
                      </div>
                      <span className="tiny-label">
                        RUN {run.run_id.slice(0, 8)}
                      </span>
                    </div>
                    <div className="filters">
                      <div className="search">
                        <Search size={15} />
                        <input
                          aria-label="Search evidence"
                          placeholder="Search manager, metric or source…"
                          value={auditSearch}
                          onChange={(e) => setAuditSearch(e.target.value)}
                        />
                      </div>
                      <select
                        aria-label="Evidence type"
                        value={auditType}
                        onChange={(e) => setAuditType(e.target.value)}
                      >
                        <option value="">All evidence types</option>
                        {[
                          "computed_metric",
                          "source_field",
                          "benchmark_observation",
                          "factor_estimate",
                          "factor_observation",
                          "macro_observation",
                          "qualitative_note",
                          "validation_result",
                          "mandate",
                        ].map((t) => (
                          <option value={t} key={t}>
                            {label(t)}
                          </option>
                        ))}
                      </select>
                    </div>
                    {memo && (
                      <div className="claim-browser">
                        <h3>Memo claims → evidence</h3>
                        {memo.claims.map((c, i) => (
                          <div key={i}>
                            <p>{c.text}</p>
                            {evidenceButtons(c)}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Evidence</th>
                            <th>Type</th>
                            <th>Value</th>
                            <th>Source / period</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {auditRows.map((e) => (
                            <tr
                              key={e.id}
                              onClick={() => openEvidence(e.id)}
                              tabIndex={0}
                              onKeyDown={(k) => {
                                if (k.key === "Enter") void openEvidence(e.id);
                              }}
                            >
                              <td>
                                <strong>{e.label}</strong>
                                <small>{e.id.split(":")[1]}</small>
                              </td>
                              <td>{label(e.type)}</td>
                              <td>
                                {e.unit === "decimal fraction" &&
                                typeof e.value.value === "number"
                                  ? pct(e.value.value)
                                  : typeof e.value.value === "number"
                                    ? num(e.value.value)
                                    : typeof e.value.value === "string"
                                      ? e.value.value.slice(0, 45)
                                      : "Structured evidence"}
                              </td>
                              <td>
                                {e.source}
                                <small>{e.observation_period}</small>
                              </td>
                              <td>
                                <span className="pill neutral">
                                  {e.live_or_cached}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="footnote">
                      Up to 500 matching entries; search and type filters reach
                      all entries.
                    </p>
                  </div>
                </>
              )}
            </>
          )}
          <footer className="workspace-footer">
            <span>
              ALLOCATOR IC COPILOT <b> / </b> INDEPENDENT PROTOTYPE
            </span>
            <span>
              Historical evidence informs diligence. It does not predict future
              returns.
            </span>
          </footer>
        </div>
      </main>
      {selected && (
        <div className="overlay" onClick={() => setSelected(null)}>
          <div
            className="drawer manager-drawer"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Manager detail"
          >
            <button
              className="close"
              onClick={() => setSelected(null)}
              aria-label="Close manager detail"
            >
              <X />
            </button>
            <div className="eyebrow">
              {selected.synthetic ? "SYNTHETIC MANAGER" : "UPLOADED MANAGER"} /
              VERIFIED ANALYTICS
            </div>
            <h2>{selected.canonical_name}</h2>
            <p className="muted">
              {selected.manager_name} · {selected.strategy} ·{" "}
              {selected.liquidity} liquidity
            </p>
            <Status eligible={selected.eligible} />
            {!selected.eligible && (
              <div className="banner error">
                <div>
                  {selected.failed_constraints.map((c, i) => (
                    <p key={i}>{c.reason}</p>
                  ))}
                </div>
              </div>
            )}
            <div className="detail-metrics">
              {(
                [
                  "annualized_return",
                  "annualized_volatility",
                  "sharpe_ratio",
                  "sortino_ratio",
                  "maximum_drawdown",
                  "benchmark_correlation",
                  "beta",
                  "alpha",
                  "tracking_error",
                  "information_ratio",
                  "upside_capture",
                  "downside_capture",
                  "calmar_ratio",
                  "best_month",
                  "worst_month",
                  "positive_month_pct",
                  "skew",
                  "kurtosis",
                ] as const
              ).map((k) => (
                <button
                  key={k}
                  onClick={() => openEvidence(selected.evidence_ids[k])}
                >
                  <span>{label(k)}</span>
                  <strong>
                    {[
                      "annualized_return",
                      "annualized_volatility",
                      "maximum_drawdown",
                      "alpha",
                      "tracking_error",
                      "best_month",
                      "worst_month",
                      "positive_month_pct",
                    ].includes(k)
                      ? pct(selected.metrics[k])
                      : num(selected.metrics[k])}
                    {k.includes("capture") && selected.metrics[k] != null
                      ? "%"
                      : ""}
                  </strong>
                  <ExternalLink size={11} />
                </button>
              ))}
            </div>
            <p className="footnote">
              {selected.metrics.observation_count} observations ·{" "}
              {selected.metrics.period_start} → {selected.metrics.period_end} ·
              benchmark overlap {selected.metrics.benchmark_observation_count}{" "}
              months · risk-free overlap{" "}
              {selected.metrics.risk_free_observation_count} months.{" "}
              {!selected.metrics.contiguous &&
                "Gapped history: annualized risk and drawdown suppressed; cumulative observed returns are incomplete."}
            </p>
            <h3>Cumulative observed return (%)</h3>
            <div className="detail-chart">
              <ResponsiveContainer>
                <LineChart data={selected.charts}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="period" minTickGap={55} />
                  <YAxis />
                  <Tooltip />
                  <Line
                    name={selected.canonical_name}
                    type="linear"
                    dataKey="fund"
                    dot={false}
                    stroke="#2c7464"
                    strokeWidth={2}
                  />
                  <Line
                    name={run?.mandate.benchmark}
                    type="linear"
                    dataKey="benchmark"
                    dot={false}
                    stroke="#b8a078"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <h3>Drawdown (%)</h3>
            <div className="detail-chart small-chart">
              <ResponsiveContainer>
                <AreaChart data={selected.charts}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="period" minTickGap={55} />
                  <YAxis />
                  <Tooltip />
                  <Area dataKey="drawdown" stroke="#9b644a" fill="#efe1d5" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <h3>Explanatory factor exposures</h3>
            <p className="muted">
              {selected.factors.status} · {selected.factors.observations} months
              · R² {pct(selected.factors.r_squared)} · estimated alpha{" "}
              {pct(selected.factors.alpha)}
            </p>
            <div className="detail-chart small-chart">
              <ResponsiveContainer>
                <BarChart
                  data={Object.entries(selected.factors.betas).map(
                    ([name, beta]) => ({ name, beta }),
                  )}
                >
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <ReferenceLine y={0} stroke="#a3aaa3" />
                  <Bar dataKey="beta" fill="#3b7768" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <h3>Diversification profile</h3>
            <div className="diversification">
              {Object.entries(selected.diversification).map(([s, c]) => (
                <button
                  key={s}
                  onClick={() =>
                    openEvidence(selected.evidence_ids[`diversification_${s}`])
                  }
                >
                  <span>{s}</span>
                  <strong>{num(c)}</strong>
                </button>
              ))}
            </div>
            <h3>Regime behavior</h3>
            <div className="diversification">
              {Object.entries(selected.regimes).map(([s, v]) => (
                <button
                  key={s}
                  onClick={() =>
                    openEvidence(selected.evidence_ids[`regime_${s}`])
                  }
                >
                  <span>{label(s)}</span>
                  <strong>{pct(v.average_return)}</strong>
                  <small>{v.observations} months</small>
                </button>
              ))}
            </div>
            <h3>Unverified qualitative note</h3>
            <p className="note">{selected.qualitative_notes}</p>
            <button
              className="text-link"
              onClick={() =>
                openEvidence(selected.evidence_ids.qualitative_notes)
              }
            >
              Inspect source note <ExternalLink size={14} />
            </button>
            <h3>Decision & score audit</h3>
            <button
              className="button"
              onClick={() => openEvidence(selected.decision_evidence)}
            >
              Eligibility, component scores and constraints{" "}
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}
      {evidence && (
        <EvidenceDrawer
          evidence={evidence}
          onClose={() => setEvidence(null)}
          onEvidence={openEvidence}
        />
      )}
    </div>
  );
}

function Stat({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="stat">
      <div>
        {title}
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{subtitle}</p>
    </div>
  );
}
function FundTable({
  funds,
  onSelect,
  compact = false,
  benchmark,
}: {
  funds: Fund[];
  onSelect: (f: Fund) => void;
  compact?: boolean;
  benchmark: string;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Rank / manager</th>
            <th>Return</th>
            <th>Volatility</th>
            <th>Sharpe</th>
            {!compact && <th>Sortino</th>}
            <th>Max DD</th>
            <th>{benchmark} corr.</th>
            {!compact && (
              <>
                <th>Factor R²</th>
                <th>History</th>
              </>
            )}
            <th>Liquidity</th>
            <th>Mandate fit</th>
          </tr>
        </thead>
        <tbody>
          {funds.map((f) => (
            <tr
              key={f.id}
              onClick={() => onSelect(f)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSelect(f);
              }}
            >
              <td>
                <div className="fund-cell">
                  <span className={`table-rank ${f.eligible ? "" : "dim"}`}>
                    {f.rank ? String(f.rank).padStart(2, "0") : "—"}
                  </span>
                  <div>
                    <strong>{f.canonical_name}</strong>
                    <small>
                      {f.strategy}
                      {f.synthetic ? " · synthetic" : ""}
                    </small>
                  </div>
                </div>
              </td>
              <td className="green-text">{pct(f.metrics.annualized_return)}</td>
              <td>{pct(f.metrics.annualized_volatility)}</td>
              <td>{num(f.metrics.sharpe_ratio)}</td>
              {!compact && <td>{num(f.metrics.sortino_ratio)}</td>}
              <td>{pct(f.metrics.maximum_drawdown)}</td>
              <td>{num(f.metrics.benchmark_correlation)}</td>
              {!compact && (
                <>
                  <td>{pct(f.factors.r_squared)}</td>
                  <td>
                    {f.metrics.observation_count}m
                    {!f.metrics.contiguous ? " ⚠" : ""}
                  </td>
                </>
              )}
              <td className="capitalize">{f.liquidity}</td>
              <td>
                <Status eligible={f.eligible} />
                {!f.eligible && (
                  <small
                    className="reason-preview"
                    title={f.failed_constraints.map((x) => x.reason).join(" ")}
                  >
                    {f.failed_constraints[0]?.reason}
                  </small>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!funds.length && <Empty text="No managers match this filter." />}
    </div>
  );
}
function RiskChart({ funds }: { funds: Fund[] }) {
  const chart = funds
    .filter(
      (f) =>
        f.metrics.annualized_return != null &&
        f.metrics.annualized_volatility != null,
    )
    .map((f) => ({
      name: f.canonical_name,
      strategy: f.strategy,
      x: f.metrics.annualized_volatility! * 100,
      y: f.metrics.annualized_return! * 100,
      sharpe: f.metrics.sharpe_ratio,
      drawdown: pct(f.metrics.maximum_drawdown),
      correlation: f.metrics.benchmark_correlation,
      eligible: f.eligible,
    }));
  return (
    <div className="risk-chart">
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 20, right: 22, bottom: 25, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e3e7e2" />
          <XAxis
            type="number"
            dataKey="x"
            name="Annualized volatility"
            unit="%"
            tickLine={false}
            axisLine={false}
            label={{
              value: "Annualized volatility (%)",
              position: "bottom",
              offset: 8,
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Annualized return"
            unit="%"
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ payload }) => {
              const f = payload?.[0]?.payload as
                (typeof chart)[number] | undefined;
              return f ? (
                <div className="chart-tooltip">
                  <strong>{f.name}</strong>
                  <p>{f.strategy}</p>
                  <p>
                    Return {f.y.toFixed(1)}% · Vol {f.x.toFixed(1)}%
                  </p>
                  <p>
                    Sharpe {num(f.sharpe)} · Drawdown {f.drawdown}
                  </p>
                  <p>
                    Correlation {num(f.correlation)} ·{" "}
                    {f.eligible ? "Eligible" : "Ineligible"}
                  </p>
                </div>
              ) : null;
            }}
          />
          <Scatter
            name="Eligible"
            data={chart.filter((f) => f.eligible)}
            fill="#347865"
          />
          <Scatter
            name="Ineligible"
            data={chart.filter((f) => !f.eligible)}
            fill="#b7beb6"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
function MandateControls({
  mandate: m,
  onChange,
}: {
  mandate: Mandate;
  onChange: (m: Mandate) => void;
}) {
  const set = <K extends keyof Mandate>(key: K, value: Mandate[K]) =>
    onChange({ ...m, [key]: value });
  return (
    <div className="mandate-controls">
      <label>
        Preference profile <span>SOFT</span>
        <select
          aria-label="Preference profile"
          value={m.profile}
          onChange={(e) =>
            onChange({ ...m, profile: e.target.value, weights: null })
          }
        >
          {["Diversifier", "Absolute Return", "Capital Preservation"].map(
            (p) => (
              <option key={p}>{p}</option>
            ),
          )}
        </select>
      </label>
      <label>
        Benchmark
        <select
          aria-label="Benchmark"
          value={m.benchmark}
          onChange={(e) => set("benchmark", e.target.value)}
        >
          {["SPY", "QQQ", "AGG", "HYG", "IWM", "TLT", "GLD"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <Control
        title="Maximum drawdown"
        value={m.maximum_drawdown * 100}
        min={0}
        max={40}
        step={1}
        suffix="%"
        set={(v) => set("maximum_drawdown", v / 100)}
      />
      <Control
        title="Target volatility"
        value={m.target_volatility * 100}
        min={1}
        max={30}
        step={1}
        suffix="%"
        soft
        set={(v) => set("target_volatility", v / 100)}
      />
      <label className="checkbox">
        <input
          type="checkbox"
          checked={m.maximum_volatility !== null}
          onChange={(e) =>
            set("maximum_volatility", e.target.checked ? 0.25 : null)
          }
        />{" "}
        Enforce maximum volatility
      </label>
      {m.maximum_volatility !== null && (
        <Control
          title="Maximum volatility"
          value={m.maximum_volatility * 100}
          min={1}
          max={60}
          step={1}
          suffix="%"
          set={(v) => set("maximum_volatility", v / 100)}
        />
      )}
      <Control
        title="Minimum history"
        value={m.minimum_track_record_months}
        min={12}
        max={60}
        step={1}
        suffix="mo"
        set={(v) => set("minimum_track_record_months", v)}
      />
      <Control
        title="Maximum correlation"
        value={m.maximum_benchmark_correlation}
        min={-1}
        max={1}
        step={0.05}
        suffix=""
        set={(v) => set("maximum_benchmark_correlation", v)}
      />
      <label>
        Liquidity requirement <span>HARD</span>
        <select
          aria-label="Liquidity requirement"
          value={m.liquidity_requirement}
          onChange={(e) => set("liquidity_requirement", e.target.value)}
        >
          {["daily", "monthly", "quarterly", "annual", "locked"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label>
        Strategy exclusions <span>HARD</span>
      </label>
      <div className="exclusions">
        {strategies.map((s) => (
          <label className="checkbox" key={s}>
            <input
              type="checkbox"
              checked={m.excluded_strategies.includes(s)}
              onChange={(e) =>
                set(
                  "excluded_strategies",
                  e.target.checked
                    ? [...m.excluded_strategies, s]
                    : m.excluded_strategies.filter((x) => x !== s),
                )
              }
            />
            {s}
          </label>
        ))}
      </div>
    </div>
  );
}
function Control({
  title,
  value,
  min,
  max,
  step,
  suffix,
  set,
  soft = false,
}: {
  title: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  set: (v: number) => void;
  soft?: boolean;
}) {
  return (
    <div className="control">
      <label htmlFor={title}>
        {title}
        <span>{soft ? "SOFT" : "HARD"}</span>
      </label>
      <div>
        <input
          id={title}
          aria-label={title}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => set(Number(e.target.value))}
        />
        <span className="number-control">
          <input
            aria-label={`${title} value`}
            type="number"
            min={min}
            max={max}
            step={step}
            value={Number(value.toFixed(3))}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (e.target.value !== "" && v >= min && v <= max) set(v);
            }}
          />
          {suffix}
        </span>
      </div>
    </div>
  );
}
function Sources({
  run,
  refresh,
  busy,
}: {
  run: Run;
  refresh: () => void;
  busy: boolean;
}) {
  return (
    <div className="panel sources">
      <div className="panel-title">
        <div>
          <h2>Market data & provenance</h2>
          <p>
            Refresh public sources explicitly. Failed providers retain labeled
            demo fallbacks.
          </p>
        </div>
        <button className="button small" disabled={busy} onClick={refresh}>
          <RefreshCw size={13} /> Refresh public data
        </button>
      </div>
      <div className="source-grid">
        {["benchmarks:SPY", "macro:TB3MS", "factors:Mkt-RF"].map((k) => {
          const s = run.sources[k];
          return s ? (
            <div key={k}>
              <Database size={17} />
              <div>
                <strong>{s.provider}</strong>
                <p>
                  {s.identifier} ·{" "}
                  {s.live_or_cached === "live" ? "LIVE" : "CACHED DEMO DATA"}
                </p>
                <small>{s.transformation}</small>
                <small>
                  Retrieved {new Date(s.retrieved_at).toLocaleString()}
                  {s.fallback_reason ? ` · fallback: ${s.fallback_reason}` : ""}
                </small>
              </div>
            </div>
          ) : null;
        })}
      </div>
      <details>
        <summary>All source statuses</summary>
        {Object.entries(run.sources).map(([k, s]) => (
          <p key={k}>
            {k} · {s.provider} · {s.live_or_cached}{" "}
            {s.fallback_reason ? `(${s.fallback_reason})` : ""}
          </p>
        ))}
      </details>
    </div>
  );
}
function EvidenceDrawer({
  evidence: e,
  onClose,
  onEvidence,
}: {
  evidence: Evidence;
  onClose: () => void;
  onEvidence: (id: string) => void;
}) {
  const [row, setRow] = useState<unknown>(null),
    [rowError, setRowError] = useState("");
  useEffect(() => {
    setRow(null);
    setRowError("");
  }, [e.id]);
  const sourceRows = Array.isArray(e.provenance?.return_sources)
    ? (e.provenance.return_sources as {
        upload_id: string;
        source_row: number;
        period: string;
        return_value: number;
      }[])
    : [];
  const sourceId =
    typeof e.provenance?.upload_id === "string" ? e.provenance.upload_id : null;
  const sourceRow =
    typeof e.provenance?.source_row === "number"
      ? e.provenance.source_row
      : null;
  async function openRow(id: string, n: number) {
    try {
      setRow(await api(`/uploads/${id}/rows/${n}`));
      setRowError("");
    } catch (err) {
      setRowError((err as Error).message);
    }
  }
  return (
    <div className="overlay evidence-overlay" onClick={onClose}>
      <div
        className="drawer evidence-drawer"
        onClick={(ev) => ev.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Evidence detail"
      >
        <button className="close" onClick={onClose} aria-label="Close evidence">
          <X />
        </button>
        <div className="eyebrow">CLAIM → EVIDENCE → SOURCE</div>
        <h2>{e.label}</h2>
        <code className="evidence-id">{e.id}</code>
        <div className="evidence-value">
          {typeof e.value.value === "number" ? (
            e.unit === "decimal fraction" ? (
              pct(e.value.value, 2)
            ) : (
              num(e.value.value, 4)
            )
          ) : typeof e.value.value === "string" ? (
            e.value.value
          ) : (
            <pre>{JSON.stringify(e.value.value, null, 2)}</pre>
          )}
          <small>{e.unit}</small>
        </div>
        <dl>
          <dt>Type</dt>
          <dd>{label(e.type)}</dd>
          <dt>Source</dt>
          <dd>{e.source}</dd>
          <dt>Observation period</dt>
          <dd>{e.observation_period}</dd>
          <dt>Data status</dt>
          <dd>{e.live_or_cached}</dd>
          <dt>Methodology</dt>
          <dd>{e.methodology}</dd>
        </dl>
        {sourceId && sourceRow && (
          <button
            className="button"
            onClick={() => openRow(sourceId, sourceRow)}
          >
            View original CSV row {sourceRow}
          </button>
        )}
        {sourceRows.length > 0 && (
          <>
            <h3>Underlying observations ({sourceRows.length})</h3>
            <div className="source-rows">
              {sourceRows.map((r) => (
                <button
                  key={r.period}
                  onClick={() => openRow(r.upload_id, r.source_row)}
                >
                  {r.period}
                  <span>{pct(r.return_value, 2)}</span>
                  <small>Source row {r.source_row}</small>
                  <ExternalLink size={12} />
                </button>
              ))}
            </div>
          </>
        )}
        {rowError && <p role="alert">{rowError}</p>}
        {row !== null && (
          <>
            <h3>Original source record</h3>
            <pre>{JSON.stringify(row, null, 2)}</pre>
          </>
        )}
        <h3>Lineage metadata</h3>
        <details>
          <summary>Inspect complete provenance</summary>
          <pre>{JSON.stringify(e.provenance, null, 2)}</pre>
        </details>
        {Boolean(e.provenance?.metric_evidence) &&
          typeof e.provenance?.metric_evidence === "object" && (
            <div className="evidence-links">
              {Object.entries(
                e.provenance!.metric_evidence as Record<string, string>,
              ).map(([k, id]) => (
                <button key={k} onClick={() => onEvidence(String(id))}>
                  {label(k)}
                </button>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}
