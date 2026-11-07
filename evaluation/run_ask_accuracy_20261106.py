import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
QUESTIONS = [
    (1, "What was Apple's Services revenue in fiscal year 2024?", ["AAPL"], "answered", [r"96[, ]169", r"services"]),
    (2, "Summarize NVIDIA's disclosed supply-chain risks.", ["NVDA"], "answered", [r"supply", r"risk"]),
    (3, "What was Microsoft's cloud revenue growth in fiscal year 2024?", ["MSFT"], "answered", [r"23\s*%", r"137[., ]?4\s*(billion|bn|\$?137\.4b)"]),
    (4, "What battery supply-chain risks does Tesla disclose?", ["TSLA"], "answered", [r"battery", r"supply|supplier|chain"]),
    (5, "What fiscal year does NVIDIA's latest 10-K cover, and when was it filed?", ["NVDA"], "answered", [r"FY?2025|2025", r"2025-02-26|February\s+26,?\s+2025"]),
    (6, "What was Apple's revenue in fiscal year 2023, and when was that report filed?", ["AAPL"], "answered", [r"383[, ]285", r"2023-11-03|November\s+3,?\s+2023"]),
    (7, "Compare Microsoft's revenue by segment between FY2023 and FY2024.", ["MSFT"], "answered", [r"211[, ]915", r"245[, ]122", r"product", r"intelligent cloud|cloud"]),
    (8, "What were NVIDIA's revenue by segment for fiscal 2024 and fiscal 2023?", ["NVDA"], "answered", [r"60[, ]922", r"26[, ]974", r"gaming|data center|professional visualization|automotive"]),
    (9, "What was Tesla's revenue by geographic region in its latest fiscal year?", ["TSLA"], "answered", [r"united states|u\.s\.|china|other international", r"revenue"]),
    (10, "What was VinFast's revenue in fiscal year 2024?", ["AAPL"], "insufficient_context", []),
    (11, "What was Apple's revenue in fiscal year 2019?", ["AAPL"], "insufficient_context", []),
    (12, "Does Tesla operate in Vietnam?", ["TSLA"], "insufficient_context", []),
    (13, "Calculate the combined revenue of Apple and Microsoft in FY2024.", ["AAPL", "MSFT"], "answered", [r"636[, ]157"]),
    (14, "What is Apple's revenue growth rate from FY2023 to FY2024?", ["AAPL"], "answered", [r"2\.02\s*%"]),
    (15, "Calculate NVIDIA's gross margin in FY2024.", ["NVDA"], "insufficient_context", []),
    (16, "Summarize NVIDIA's disclosed risks.", ["NVDA"], "answered", [r"risk"]),
    (17, "What risks does NVIDIA disclose about supply chain?", ["NVDA"], "answered", [r"risk", r"supply|supplier|chain"]),
]


def request(question, tickers):
    payload = {"query": question, "top_k": 10, "language": "en", "tickers": tickers, "form_types": ["10-K"]}
    if question.startswith("What was Apple's revenue in fiscal year 2019"):
        payload.update(filing_date_start="2024-01-01", filing_date_end="2024-12-31")
    req = urllib.request.Request(BASE + "/api/ask", json.dumps(payload).encode(), {"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {"error": "non-JSON HTTP error"}
    except Exception as exc:
        return None, {"error": str(exc)}


rows = []
for number, question, tickers, expected_status, criteria in QUESTIONS:
    code, body = request(question, tickers)
    text = body.get("answer", "") if isinstance(body, dict) else ""
    status = body.get("status") if isinstance(body, dict) else None
    citations = body.get("citations", []) if isinstance(body, dict) else []
    if code == 200 and status == expected_status:
        checks = [bool(re.search(pattern, text, re.I)) for pattern in criteria]
        correct = all(checks) and (status != "answered" or bool(citations))
        if expected_status == "insufficient_context":
            correct = not citations and not re.search(r"\b\d[\d,.]*\b", text)
    else:
        checks = []
        correct = False
    rows.append({"id": number, "query": question, "expected_status": expected_status, "http_status": code,
                 "actual_status": status, "correct": bool(correct), "criteria_passed": checks,
                 "answer": text, "citation_count": len(citations), "citations": citations,
                 "retrieval": body.get("retrieval") if isinstance(body, dict) else None,
                 "error": body.get("error") if isinstance(body, dict) else None})
    print(f"{number:02d}: {'PASS' if correct else 'FAIL'} ({code}, {status})", flush=True)
    time.sleep(0.2)

summary = {"total": len(rows), "correct": sum(row["correct"] for row in rows),
           "accuracy": sum(row["correct"] for row in rows) / len(rows),
           "scope": "Live /api/ask answers; exact numeric criteria for quantitative questions and abstention/citation criteria for other questions.",
           "rows": rows}
json_path = Path("evaluation/ask_accuracy_20261106.json")
md_path = Path("evaluation/ask_accuracy_20261106.md")
json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
lines = ["# Live Answer Accuracy Report", "", f"- Correct: {summary['correct']}/{summary['total']} ({summary['accuracy']:.1%})", "- Endpoint: `/api/ask` with the filters specified in the question set.", "- Scoring: exact expected status, required answer facts for quantitative questions, and at least one citation for answered responses; no numeric claims or citations for insufficient-context responses.", "", "| # | Expected | Actual | Citations | Result | Answer |", "|---:|---|---|---:|:---:|---|"]
for row in rows:
    answer = row["answer"].replace("|", "\\|").replace("\n", " ")
    lines.append(f"| {row['id']} | {row['expected_status']} | {row['actual_status'] or 'error'} | {row['citation_count']} | {'PASS' if row['correct'] else 'FAIL'} | {answer} |")
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {json_path.resolve()} and {md_path.resolve()}; {summary['correct']}/{summary['total']} correct")
