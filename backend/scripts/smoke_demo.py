"""Executable five-minute API journey. --ai makes real calls; --refresh tests public sources."""

import argparse
import json
import urllib.request
import urllib.error
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--ai", action="store_true")
parser.add_argument("--refresh", action="store_true")
parser.add_argument("--output-dir", type=Path, help="Save actual AI acceptance artifacts and Word exports here")
args = parser.parse_args()


def call(path, body=None):
    request = urllib.request.Request(
        "http://localhost:8000/api" + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # The app sanitizes provider failures; never dump provider bodies or credentials.
        detail = json.load(exc).get("detail", "Request failed")
        raise SystemExit(f"Acceptance blocked: {path} returned HTTP {exc.code}: {detail}") from None


if args.refresh:
    result = call("/market/refresh", {})
    print("Actual source status:", result["result"]["market_status"])
    print(
        {
            k: {"provider": v["provider"], "status": v["live_or_cached"], "fallback": v.get("fallback_reason")}
            for k, v in result["sources"]["benchmarks"].items()
        }
    )
seed = call("/demo", {})
r = seed["result"]
assert len(r["funds"]) == 18
print("Baseline:", [(f["canonical_name"], f["rank"]) for f in r["funds"] if f["eligible"]])
assert call("/data-health")["categories"]["duplicate_observation"]
base = dict(r["mandate"])
base["maximum_drawdown"] = 0.07
r = call("/evaluations", {"mandate": base, "previous_run_id": r["run_id"]})
assert not next(f for f in r["funds"] if f["id"] == "ATLAS")["eligible"]
print("Drawdown transition:", next(c for c in r["changes"] if c["fund_id"] == "ATLAS")["reasons"])
base["liquidity_requirement"] = "monthly"
r = call("/evaluations", {"mandate": base, "previous_run_id": r["run_id"]})
assert not next(f for f in r["funds"] if f["id"] == "ORION")["eligible"]
print("Liquidity transition:", next(c for c in r["changes"] if c["fund_id"] == "ORION")["reasons"])
brief = call("/memos", {"run_id": r["run_id"], "kind": "briefing"})
for c in brief["claims"]:
    for eid in c["evidence_ids"]:
        assert call("/evidence/" + eid)["id"] == eid
print("Rules-based briefing:", len(brief["claims"]), "claims; all citations resolve")
if args.ai:
    for kind in ["memo", "challenge"]:
        memo = call("/memos", {"run_id": r["run_id"], "kind": kind})
        assert memo["model_metadata"]["ai_generated"]
        saved = call("/memos?run_id=" + r["run_id"])
        assert any(m["id"] == memo["id"] and m["payload"] == memo["payload"] for m in saved)
        for claim in memo["claims"]:
            assert claim["evidence_ids"]
            for eid in claim["evidence_ids"]:
                evidence = call("/evidence/" + eid)
                assert evidence["id"] == eid and evidence["run_id"] == r["run_id"]
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / f"{kind}.json").write_text(json.dumps(memo, indent=2))
            for full in [False, True]:
                url = f"http://localhost:8000/api/runs/{r['run_id']}/memo.docx?memo_id={memo['id']}&include_evidence={str(full).lower()}"
                with urllib.request.urlopen(url, timeout=30) as response:
                    content = response.read()
                assert content.startswith(b"PK")
                (args.output_dir / f"{kind}{'-evidence' if full else ''}.docx").write_bytes(content)
        print("Live", kind, ":", len(memo["claims"]), "validated claims;", memo["model_metadata"]["model"])
print("Demo journey passed")
