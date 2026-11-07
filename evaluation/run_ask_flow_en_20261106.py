import json
import re
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

BASE = "http://127.0.0.1:8000"
DATASET = Path("evaluation/ask_flow_questions_en_20261106.json")
OUTPUT_JSON = Path("evaluation/ask_flow_results_en_20261106.json")
OUTPUT_MD = Path("evaluation/ask_flow_results_en_20261106.md")


def call(case):
    payload = {
        "query": case["question"],
        "top_k": case.get("top_k", 10),
        "language": "en",
        "form_types": case.get("form_types"),
    }
    if case.get("tickers"):
        payload["tickers"] = case["tickers"]
    request = urllib.request.Request(
        BASE + "/api/ask",
        json.dumps(payload).encode("utf-8"),
        {"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.status, json.loads(response.read()), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"error": {"code": "non_json_http_error"}}
        return exc.code, body, (time.perf_counter() - started) * 1000
    except Exception as exc:
        return None, {"error": {"code": type(exc).__name__, "message": str(exc)}}, (time.perf_counter() - started) * 1000


def has_signal(text, alternatives):
    normalized = text.lower()
    return any(value.lower() in normalized for value in alternatives)


def score(case, http_status, body):
    actual = body.get("status") if isinstance(body, dict) else None
    expected = case["expected_status"]
    accepted = expected if isinstance(expected, list) else [expected]
    if http_status != 200 or actual not in accepted:
        return False, []
    citations = body.get("citations", [])
    if actual == "insufficient_context":
        return len(citations) == 0, []
    checks = [has_signal(body.get("answer", ""), group) for group in case.get("signals", [])]
    citation_ok = len(citations) >= case.get("min_citations", 1)
    return all(checks) and citation_ok, checks


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


dataset = json.loads(DATASET.read_text(encoding="utf-8"))
rows = []
for index, case in enumerate(dataset["cases"], 1):
    http_status, body, latency = call(case)
    passed, checks = score(case, http_status, body)
    error = body.get("error") if isinstance(body, dict) else None
    row = {
        "id": case["id"], "category": case["category"], "question": case["question"],
        "expected_status": case["expected_status"], "http_status": http_status,
        "actual_status": body.get("status") if isinstance(body, dict) else None,
        "passed": passed, "signal_checks": checks,
        "latency_ms": round(latency, 1),
        "server_total_ms": (body.get("timings_ms") or {}).get("total") if isinstance(body, dict) else None,
        "retrieval_ms": (body.get("timings_ms") or {}).get("retrieval") if isinstance(body, dict) else None,
        "generation_ms": (body.get("timings_ms") or {}).get("generation") if isinstance(body, dict) else None,
        "citation_count": len(body.get("citations", [])) if isinstance(body, dict) else 0,
        "answer": body.get("answer", "") if isinstance(body, dict) else "",
        "error_code": error.get("code") if isinstance(error, dict) else None,
    }
    rows.append(row)
    print(f"{index:02d}/25 {case['id']}: {'PASS' if passed else 'FAIL'} | HTTP {http_status} | {row['actual_status'] or row['error_code']} | {latency:.0f} ms", flush=True)
    time.sleep(0.15)

latencies = [row["latency_ms"] for row in rows]
answered = sum(row["actual_status"] == "answered" for row in rows)
insufficient = sum(row["actual_status"] == "insufficient_context" for row in rows)
errors = Counter(row["error_code"] for row in rows if row["error_code"])
by_category = defaultdict(lambda: {"total": 0, "passed": 0, "latencies": []})
for row in rows:
    group = by_category[row["category"]]
    group["total"] += 1
    group["passed"] += int(row["passed"])
    group["latencies"].append(row["latency_ms"])
category_summary = [
    {"category": category, "total": values["total"], "passed": values["passed"],
     "pass_rate": values["passed"] / values["total"],
     "mean_latency_ms": round(statistics.mean(values["latencies"]), 1)}
    for category, values in sorted(by_category.items())
]
summary = {
    "total": len(rows), "passed": sum(row["passed"] for row in rows),
    "pass_rate": sum(row["passed"] for row in rows) / len(rows),
    "http_200": sum(row["http_status"] == 200 for row in rows),
    "answered": answered, "insufficient_context": insufficient,
    "errors": dict(errors),
    "latency_ms": {
        "mean": round(statistics.mean(latencies), 1), "median": round(statistics.median(latencies), 1),
        "p95": round(percentile(latencies, .95), 1), "min": min(latencies), "max": max(latencies),
    },
    "categories": category_summary,
}
OUTPUT_JSON.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

lines = [
    "# English `/api/ask` Performance Report", "",
    f"- Passed: **{summary['passed']}/{summary['total']} ({summary['pass_rate']:.1%})**",
    f"- HTTP 200: **{summary['http_200']}/{summary['total']}**",
    f"- Results: answered={answered}, insufficient_context={insufficient}, errors={sum(errors.values())}",
    f"- Client latency: mean={summary['latency_ms']['mean']:.1f} ms, median={summary['latency_ms']['median']:.1f} ms, p95={summary['latency_ms']['p95']:.1f} ms, min={summary['latency_ms']['min']:.1f} ms, max={summary['latency_ms']['max']:.1f} ms",
    f"- Error codes: `{dict(errors)}`", "",
    "## Category summary", "",
    "| Category | Passed | Pass rate | Mean latency (ms) |", "|---|---:|---:|---:|",
]
for group in category_summary:
    lines.append(f"| {group['category']} | {group['passed']}/{group['total']} | {group['pass_rate']:.1%} | {group['mean_latency_ms']:.1f} |")
lines += ["", "## Per-question results", "", "| ID | Category | Expected | Actual | HTTP | Citations | Latency (ms) | Result |", "|---|---|---|---|---:|---:|---:|:---:|"]
for row in rows:
    expected = row["expected_status"] if isinstance(row["expected_status"], str) else "/".join(row["expected_status"])
    actual = row["actual_status"] or row["error_code"] or "error"
    lines.append(f"| {row['id']} | {row['category']} | {expected} | {actual} | {row['http_status'] or '—'} | {row['citation_count']} | {row['latency_ms']:.1f} | {'PASS' if row['passed'] else 'FAIL'} |")
OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"summary": summary, "json": str(OUTPUT_JSON.resolve()), "markdown": str(OUTPUT_MD.resolve())}, ensure_ascii=False), flush=True)
