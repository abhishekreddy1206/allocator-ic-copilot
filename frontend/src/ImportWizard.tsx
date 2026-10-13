import { useEffect, useState } from "react";
import { useDialogFocus } from "./useDialogFocus";
import { X, RefreshCw, Check } from "lucide-react";
import { api, label } from "./api";
import type { Run } from "./types";

type Preview = {
  headers: string[];
  rows: { source_row: number; values: Record<string, string> }[];
  row_count: number;
  sheets: string[];
  sheet: string;
  mapping: Record<string, string>;
  fields: string[];
  required: string[];
  validation_error?: string;
  summary?: {
    valid_rows: number;
    errors: number;
    warnings: number;
    already_imported?: boolean;
  };
  issues?: {
    source_row: number | null;
    severity: string;
    description: string;
    issue_type: string;
  }[];
  issues_limited?: boolean;
};

export default function ImportWizard({
  file,
  close,
  imported,
}: {
  file: File;
  close: () => void;
  imported: (run: Run) => Promise<void>;
}) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [corrections, setCorrections] = useState<
    Record<string, Record<string, string>>
  >({});
  const [sheet, setSheet] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [page, setPage] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const dialog = useDialogFocus(true, () => {
    if (!busy) close();
  });
  function form() {
    const body = new FormData();
    body.append("file", file);
    body.append("mapping", JSON.stringify(mapping));
    body.append("corrections", JSON.stringify(corrections));
    body.append("sheet", sheet);
    return body;
  }
  useEffect(() => {
    let active = true;
    const body = new FormData();
    body.append("file", file);
    api<Preview>("/imports/preview", { method: "POST", body })
      .then((p) => {
        if (active) {
          setPreview(p);
          setMapping(p.mapping);
          setSheet(p.sheet);
          setReviewed(!p.validation_error);
        }
      })
      .catch((e: Error) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [file]);
  async function validate() {
    setBusy(true);
    setError("");
    setReviewed(false);
    setConfirmed(false);
    try {
      const p = await api<Preview>("/imports/preview", {
        method: "POST",
        body: form(),
      });
      setPreview(p);
      setMapping(p.mapping);
      setSheet(p.sheet);
      setReviewed(!p.validation_error);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function commit() {
    setBusy(true);
    setError("");
    try {
      const r = await api<{ result: Run }>("/imports/commit", {
        method: "POST",
        body: form(),
      });
      await imported(r.result);
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const invalidate = () => {
    setReviewed(false);
    setConfirmed(false);
  };
  return (
    <div className="overlay">
      <div
        className="import-dialog"
        ref={dialog}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label="Review manager import"
      >
        <button
          className="close"
          aria-label="Close import"
          disabled={busy}
          onClick={close}
        >
          <X />
        </button>
        <div className="eyebrow">REVIEW BEFORE IMPORT</div>
        <h1>Bring your manager data</h1>
        <p>{file.name} · Nothing is saved until you confirm the import.</p>
        <p className="footnote">
          Use one monthly observation per row, with headers in the first row.
          Returns must be decimals or explicit percentages. XLSX dates and
          percentage formatting are recognized; formulas require verified
          replacement values.
        </p>
        {error && (
          <div className="banner error" role="alert">
            {error}
          </div>
        )}
        {busy && <p role="status">Checking manager data…</p>}
        {preview && (
          <>
            {!!preview.sheets.length && (
              <label className="import-sheet">
                Worksheet
                <select
                  aria-label="Worksheet"
                  value={sheet}
                  disabled={busy}
                  onChange={(e) => {
                    setSheet(e.target.value);
                    setMapping({});
                    setCorrections({});
                    setPage(0);
                    invalidate();
                  }}
                >
                  {preview.sheets.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
                <span>Choose a sheet, then update the preview.</span>
              </label>
            )}
            <h2>1. Match your columns</h2>
            <div className="mapping-grid">
              {preview.headers.map((h) => (
                <label key={h}>
                  {h}
                  <select
                    aria-label={`Map ${h}`}
                    disabled={busy}
                    value={mapping[h] || ""}
                    onChange={(e) => {
                      setMapping({ ...mapping, [h]: e.target.value });
                      invalidate();
                    }}
                  >
                    <option value="">Ignore column</option>
                    {preview.fields.map((f) => (
                      <option key={f} value={f}>
                        {label(f)}
                        {preview.required.includes(f) ? " *" : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <p className="footnote">
              * Required fields. Each field can be matched to one column.
            </p>
            <h2>2. Review and correct values</h2>
            <p>
              Edit a cell, then update the preview. Corrections are logged
              alongside the original file.
            </p>
            {preview.validation_error && (
              <div className="banner error">{preview.validation_error}</div>
            )}
            {preview.summary && (
              <div className="import-summary">
                <strong>
                  {preview.summary.valid_rows} new accepted observations
                </strong>
                <span>
                  {preview.summary.errors} errors · {preview.summary.warnings}{" "}
                  warnings · {preview.row_count} source rows
                </span>
                {preview.summary.already_imported && (
                  <span>This reviewed version was already imported.</span>
                )}
              </div>
            )}
            <div className="table-scroll">
              <table className="import-table">
                <thead>
                  <tr>
                    <th>Source row</th>
                    {preview.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.slice(page * 10, page * 10 + 10).map((row) => (
                    <tr key={row.source_row}>
                      <td>{row.source_row}</td>
                      {preview.headers.map((h) => (
                        <td key={h}>
                          <input
                            aria-label={`Row ${row.source_row} ${h}`}
                            value={
                              corrections[String(row.source_row)]?.[h] ??
                              row.values[h] ??
                              ""
                            }
                            disabled={busy}
                            onChange={(e) => {
                              setCorrections({
                                ...corrections,
                                [String(row.source_row)]: {
                                  ...corrections[String(row.source_row)],
                                  [h]: e.target.value,
                                },
                              });
                              invalidate();
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="import-pagination">
              <button
                className="button small"
                disabled={page === 0 || busy}
                onClick={() => setPage(page - 1)}
              >
                Previous rows
              </button>
              <span>
                Rows {page * 10 + 1}–
                {Math.min(page * 10 + 10, preview.rows.length)} of{" "}
                {preview.row_count}
                {preview.row_count > 200 ? " · first 200 editable here" : ""}
              </span>
              <button
                className="button small"
                disabled={(page + 1) * 10 >= preview.rows.length || busy}
                onClick={() => setPage(page + 1)}
              >
                Next rows
              </button>
            </div>
            <div className="import-issues">
              {preview.issues
                ?.filter((i) => i.severity !== "info")
                .map((i, n) => (
                  <p key={n}>
                    <strong>
                      {i.source_row ? `Row ${i.source_row}` : "History"} ·{" "}
                      {i.severity}
                    </strong>{" "}
                    {i.description}
                  </p>
                ))}
              {preview.issues_limited && (
                <p>
                  Showing a limited issue preview. The full ledger will be
                  available in Data Health.
                </p>
              )}
            </div>
            <button
              className="button"
              disabled={busy}
              onClick={() => void validate()}
            >
              <RefreshCw size={15} /> Update preview
            </button>
            <h2>3. Confirm the reviewed import</h2>
            <label className="import-confirm">
              <input
                type="checkbox"
                checked={confirmed}
                disabled={busy || !reviewed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />{" "}
              I reviewed the mapping and issues. Valid observations will be
              saved; rejected rows remain in the issue ledger.
            </label>
            <p className="footnote">
              Conflicting existing returns are retained and flagged, never
              overwritten. You can fix quarantined rows in this preview;
              existing accepted observations require a separate controlled
              revision workflow.
            </p>
            <button
              className="button primary"
              disabled={busy || !reviewed || !confirmed || !preview.summary}
              onClick={() => void commit()}
            >
              <Check size={15} /> Confirm import
            </button>
          </>
        )}
      </div>
    </div>
  );
}
