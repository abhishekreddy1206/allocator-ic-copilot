"""Executable five-minute API journey. --ai makes real calls; --refresh tests public sources."""

import argparse
import json
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--ai", action="store_true")
parser.add_argument("--refresh", action="store_true")
args = parser.parse_args()


def call(path, body=None):
    request = urllib.request.Request(
        "http://localhost:8000/api" + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


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
        for claim in memo["claims"]:
            assert claim["evidence_ids"]
            for eid in claim["evidence_ids"]:
                assert call("/evidence/" + eid)["id"] == eid
        print("Live", kind, ":", len(memo["claims"]), "validated claims;", memo["model_metadata"]["model"])
print("Demo journey passed")
