# Live Answer Accuracy Report

- Correct: 4/17 (23.5%)
- Endpoint: `/api/ask` with the filters specified in the question set.
- Scoring: exact expected status, required answer facts for quantitative questions, and at least one citation for answered responses; no numeric claims or citations for insufficient-context responses.

| # | Expected | Actual | Citations | Result | Answer |
|---:|---|---|---:|:---:|---|
| 1 | answered | error | 0 | FAIL |  |
| 2 | answered | error | 0 | FAIL |  |
| 3 | answered | answered | 1 | PASS | In fiscal year 2024, Microsoft Cloud revenue increased by 23% to $137.4 billion. [S3] |
| 4 | answered | error | 0 | FAIL |  |
| 5 | answered | answered | 1 | FAIL | NVIDIA's latest 10-K covers fiscal year 2025 [S1]. While the provided sources discuss the content of the FY2025 10-K, they do not explicitly state the specific filing date for the current 2025 report [S1]. |
| 6 | answered | insufficient_context | 0 | FAIL | The provided sources do not disclose the total revenue for Apple Inc. in fiscal year 2023. |
| 7 | answered | insufficient_context | 0 | FAIL |  |
| 8 | answered | insufficient_context | 0 | FAIL | The provided documents do not state the total revenue by reportable segment (Compute & Networking and Graphics) for fiscal years 2024 and 2023; the provided table in source S1 presents operating income by reportable segment, not revenue by segment. |
| 9 | answered | insufficient_context | 0 | FAIL |  |
| 10 | insufficient_context | insufficient_context | 0 | PASS |  |
| 11 | insufficient_context | insufficient_context | 0 | PASS |  |
| 12 | insufficient_context | insufficient_context | 0 | PASS |  |
| 13 | answered | insufficient_context | 0 | FAIL | There is not enough sourced data with compatible periods and units to calculate this. |
| 14 | answered | insufficient_context | 0 | FAIL | There is not enough sourced data with compatible periods and units to calculate this. |
| 15 | insufficient_context | answered | 1 | FAIL | NVIDIA Corporation's gross margin was 72.7% for fiscal year 2024. [S1] |
| 16 | answered | error | 0 | FAIL |  |
| 17 | answered | error | 0 | FAIL |  |
